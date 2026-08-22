// EL RESUM DEL MODEL AMB EL WIZARD PARTIT EN SUBESPAIS
// (NORMA_LAYOUT §8f · evidència PROPOSTA_resum_wizard_partit.html · ratificat Agus 08/08).
//
// ── QUÈ CANVIA, I PER QUÈ NO ÉS PELL ──────────────────────────────────────────────────────
// El wizard de model era una pantalla a part amb quatre passos en fila: per canviar la talla
// base d'un model calia SORTIR de la fitxa, recórrer el wizard i tornar. La §8f el parteix:
//
//   · ESQUERRA «Informació» = el pas 1 (Identificació). «Editar» obre el formulari AL MATEIX
//     LLOC on després es llegeix, mai en una pantalla a part.
//   · DRETA «Definició del model» = LA COLUMNA DE TREBALL, amb els passos 2 · Peça, 3 · Talles
//     i 4 · Graduació com a SUBESPAIS separats, cadascun amb les seves accions dins del seu
//     espai. El model no desapareix mai de la vista.
//
// ── LES TRES LLEIS DEL SUBESPAI (llenguatge del stepper, §6) ──────────────────────────────
//   FET       `--ok` + ✓, amb **les eleccions FIXADES I VISIBLES** (chips verds d'inclusió +
//             els valors escrits) i «Canviar» en secundari. Res s'amaga en tancar-se.
//   ACTUAL    `--sel` + filet d'or, el formulari a dins, i **el seu desar és l'ÚNIC BLAU**.
//   BLOQUEJAT tènue **amb el motiu escrit** («requereix talles»), mai un pas mut i apagat.
//
// ── EL BLAU DEPÈN DE L'ESTAT (§8f) ────────────────────────────────────────────────────────
// El blau assenyala el pas pendent i CALLA quan està fet. Per això «Editar» de la columna
// esquerra és primari mentre la definició no està completa i baixa a secundari quan ho està:
// en un model nou, el primer que has de fer és dir qui és.
//
// ── QUÈ ES COMPARTEIX AMB EL WIZARD, I QUÈ NO ─────────────────────────────────────────────
// Aquesta és la **germana de presentació** dels passos 2-4: mateix domini, mateixa decisió,
// altra pell. El que decideix va a mòduls compartits (`utils/talles`, `utils/proximitatRun`,
// `CascadeFinder`, `RuleSetPicker`, `useConfirmacioRuleset`, `useEixos`) i el wizard els importa
// dels mateixos llocs — **el wizard vell no es toca ni es trenca**.
//
// El que ha deixat de ser cert (Agus, QA 09/08) és que el wizard fos la VÀLVULA D'ESCAPAMENT de
// la graduació: el pas 4 també edita AQUÍ, i cap dels tres subespais treu ja de la fitxa. El
// wizard segueix existint i fent la seva feina —crear— però no és el lloc on s'ha d'anar a
// acabar un model que ja existeix. V. la capçalera de `PasGraduacio`.
//
// ── PER QUÈ CADA SUBESPAI POT DESAR SOL, SENSE BACKEND NOU ────────────────────────────────
// `PATCH /models/<id>/update-step2/` ja resol camp a camp: `_resolve_garment_def` **només
// escriu el que ve al payload** (views.py:720). Un PATCH que parla de talles no toca la peça,
// i un que no parla de graduació no toca cap regla (el predicat `canvia_joc` mira que el joc
// entri al payload **i** que sigui un altre). O sigui que partir el desat no demana endpoint
// nou: demana enviar menys.
import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import CascadeFinder from '../CascadeSelector/CascadeFinder'
import CustomerSelector from '../CustomerSelector'
import { useEixos } from '../grading/eixosFont'
import RuleSetPicker from '../grading/RuleSetPicker'
import useConfirmacioRuleset from './useConfirmacioRuleset'
import { models, sizeSystems, gradingRuleSets, garmentGroups, customers } from '../../api/endpoints'
import PecaDefinicioContenidor, { BotoCanviar, FilaDefinicio, ValorCamp }
  from './PecaDefinicioContenidor'
import { ORIGEN, origenDeLaFila, seguentCodiDePeca } from '../../utils/pecaDefinicio'
import { ordenaPerProximitat } from '../../utils/proximitatRun'
import { labelsOf, ordenaPelSistema } from '../../utils/talles'
import Feedback from '../ui/Feedback'
import Modal from '../ui/Modal'
import useToc, { anellFocus } from '../ui/toc'

const MONO = 'IBM Plex Mono, monospace'

// ── ÀTOMS DE LA NORMA ──────────────────────────────────────────────────────────────────────

// §1 · «INCLÒS EN LA DEFINICIÓ» = VERD (fons --ok-bg, tinta i vora --ok, pes 600). No és «on
// soc»: marcar és confirmar, no navegar. El repòs és filet --line sobre --panel; el hover,
// `--sel`, que NO trepitja el verd. Tres estats i cap més (el quart era l'anell de focus).
function Xip({ marcat, onClick, disabled, children, title }) {
  const [toc, gestos] = useToc()
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={title}
      aria-pressed={marcat} {...gestos}
      style={{
        fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
        padding: '3px 10px', borderRadius: 'var(--r-pill)',
        borderWidth: 1, borderStyle: 'solid',
        borderColor: marcat ? 'var(--ok)' : 'var(--line)',
        background: marcat ? 'var(--ok-bg)' : (toc.hover && !disabled ? 'var(--sel)' : 'var(--panel)'),
        color: marcat ? 'var(--ok)' : 'var(--text-main)',
        fontWeight: marcat ? 600 : 400,
        cursor: disabled ? 'not-allowed' : 'pointer',
        outline: 'none',
        ...(toc.focus ? anellFocus : null),
      }}>
      {children}
    </button>
  )
}

// §1 · badge NEUTRE (fons suau + tinta principal + filet fi). El de sistema porta el filet de
// la casa (`--gold-border`), que és el que la maqueta dona a `.b.sys`.
function BadgeNeutre({ casa = false, children, title }) {
  return (
    <span title={title} style={{
      display: 'inline-flex', alignItems: 'center',
      fontSize: 'var(--fs-caption)', lineHeight: '12px', fontWeight: 600, letterSpacing: '.04em',
      padding: '3px 10px', borderRadius: 'var(--r-pill)', whiteSpace: 'nowrap',
      background: 'var(--sel)', color: 'var(--text-main)',
      borderWidth: 1, borderStyle: 'solid',
      borderColor: casa ? 'var(--gold-border)' : 'var(--line)',
    }}>{children}</span>
  )
}

function Boto({ variant = 'sec', onClick, disabled, children, style, ...rest }) {
  const [toc, gestos] = useToc()
  const base = {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 500, lineHeight: '16px',
    borderRadius: 'var(--r-ctrl)', padding: '8px 16px',
    borderWidth: 1, borderStyle: 'solid',
    cursor: disabled ? 'not-allowed' : 'pointer', outline: 'none',
  }
  const pell = variant === 'pri'
    // §5.1 · PRIMÀRIA: fons --accio + tinta blanca. És «l'acció que completa la feina d'aquí».
    ? { background: 'var(--accio)', borderColor: 'var(--accio)', color: 'var(--white)' }
    : variant === 'ter'
      // §5.4 · TERCIÀRIA: text sol, hover --sel. Reserva el gruix de la vora per no saltar.
      ? { background: toc.hover ? 'var(--sel)' : 'none', borderColor: 'transparent', color: 'var(--text-soft)' }
      // §5.2 · SECUNDÀRIA: blanc + vora --gold-border + tinta fosca, padding 8×16.
      : { background: toc.hover ? 'var(--sel)' : 'var(--panel)', borderColor: 'var(--gold-border)', color: 'var(--text-main)' }
  // §5.7 · deshabilitat: BAIXA EL FONS, no la tinta.
  const apagat = disabled ? { background: 'var(--bg-page)', borderColor: 'var(--line)', color: 'var(--text-faint)' } : null
  return (
    <button type="button" onClick={onClick} disabled={disabled} {...gestos} {...rest}
      style={{ ...base, ...pell, ...apagat, ...(toc.focus ? anellFocus : null), ...style }}>
      {children}
    </button>
  )
}

const camp = {
  width: '100%', fontFamily: MONO, fontSize: 'var(--fs-body)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
  background: 'var(--panel)', color: 'var(--text-main)', boxSizing: 'border-box',
}
const retolCamp = {
  fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.05em',
  textTransform: 'uppercase', color: 'var(--text-soft)',
}
const buitText = { color: 'var(--text-faint)', fontStyle: 'italic' }

/**
 * El text d'un error de vora, tal com el servidor el redacta.
 *
 * L'ordre no és casual: la porta de peces posa la frase humana a `error` i el CODI a `codi`
 * (`garment_duplicat`, `talles_desconegudes`…). El codi és el contracte i el text pot canviar,
 * o sigui que aquí es MOSTRA el text i no es tradueix el codi: reescriure'l a la pantalla faria
 * que API i pantalla expliquessin el mateix de dues maneres, que és el defecte que
 * `useConfirmacioRuleset` ja va tancar amb el seu `message`.
 */
function missatgeError(e, t) {
  const d = e?.response?.data
  return d?.error || d?.message || d?.detail || t('resum_wizard.save_error')
}

// La targeta contenidora dels dos costats (§8b·4: blanca, filet --line, radi 12).
function Targeta({ titol, nota, accions, children, cos = true }) {
  return (
    <div style={{
      background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)', overflow: 'hidden',
      fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
        borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)',
      }}>
        <span style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600 }}>{titol}</span>
        {nota && <span style={{
          fontSize: 'var(--fs-label)', letterSpacing: '.05em', textTransform: 'uppercase',
          color: 'var(--text-faint)',
        }}>{nota}</span>}
        {accions && <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>{accions}</span>}
      </div>
      {cos ? <div style={{ padding: '14px 16px' }}>{children}</div> : children}
    </div>
  )
}

function Fila({ etiqueta, children }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '132px 1fr', gap: 8, padding: '6px 0',
      borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line-soft)',
      alignItems: 'baseline',
    }}>
      <span style={retolCamp}>{etiqueta}</span>
      <span style={{ fontSize: 'var(--fs-body)' }}>{children}</span>
    </div>
  )
}

// ── EL SUBESPAI ────────────────────────────────────────────────────────────────────────────
// Els quatre estats de la §6, amb el numeral que la maqueta dibuixa. `motiu` només existeix a
// BLOQUEJAT i és OBLIGATORI: un pas apagat sense motiu escrit no és un estat, és una avaria.
function Subespai({ num, titol, estat, motiu, accions, onObrir, children }) {
  const fet = estat === 'fet'
  const ara = estat === 'ara'
  const blocat = estat === 'blocat'
  const tintaCap = fet ? 'var(--ok)' : blocat ? 'var(--text-faint)' : 'var(--text-main)'
  return (
    <div style={{
      borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)',
    }}>
      <div
        onClick={blocat ? undefined : onObrir}
        style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
          color: tintaCap,
          cursor: blocat ? 'not-allowed' : (onObrir ? 'pointer' : 'default'),
          background: ara ? 'var(--sel)' : undefined,
          boxShadow: ara ? 'inset 3px 0 0 var(--gold)' : undefined,
        }}>
        <span style={{
          width: 20, height: 20, borderRadius: '50%', flex: 'none',
          borderWidth: 1, borderStyle: 'solid',
          borderColor: fet ? 'var(--ok)' : ara ? 'var(--gold)' : blocat ? 'var(--text-faint)' : 'var(--text-soft)',
          background: fet ? 'var(--ok)' : 'transparent',
          color: fet ? 'var(--white)' : ara ? 'var(--gold)' : 'inherit',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 'var(--fs-caption)', fontWeight: 700,
        }}>{fet ? '✓' : num}</span>
        <span style={{ fontWeight: 600, color: fet ? 'var(--text-main)' : 'inherit' }}>{titol}</span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* BLOQUEJAT AMB EL MOTIU ESCRIT — la §8f no accepta un pas apagat i mut. */}
          {blocat && <span style={{ fontSize: 'var(--fs-caption)' }}>{motiu}</span>}
          {accions}
        </span>
      </div>
      {children && <div style={{ padding: '0 16px 14px 46px' }}>{children}</div>}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════════════════

export default function ResumWizardPartit({ model, onUpdated }) {
  const { t } = useTranslation()
  const { targets: catTargets, constructions: catConstructions, fits: catFits } = useEixos()
  const [feedback, setFeedback] = useState(null)
  // Quin subespai està OBERT. `null` = mana l'estat (el primer pendent és l'ACTUAL); un número
  // = l'usuari ha premut «Canviar» sobre un pas ja fet i vol tornar-hi.
  const [obert, setObert] = useState(null)
  const [editantInfo, setEditantInfo] = useState(false)
  // LES PRENDES DEL MODEL, servides pel contracte de T2-bis. La mare hi ve sintètica i sempre
  // primera, de manera que aquest estat mai és buit un cop carregat i la pantalla no ha de
  // saber si el model té peces per saber què pintar: recorre la llista i prou.
  const [peces, setPeces] = useState([])
  // La peça que s'està mirant d'esborrar. `null` = cap diàleg obert.
  const [aEsborrar, setAEsborrar] = useState(null)

  const id = model?.id
  // ── L'ESTAT DE CADA PAS, llegit del MODEL (mai d'estat local paral·lel) ───────────────
  const pecaFeta = !!model?.garment_type_item
  const tallesFetes = !!(model?.size_system && model?.size_run_model && model?.base_size_label)
  const gradFeta = !!model?.grading_rule_set
  const fets = [pecaFeta, tallesFetes, gradFeta].filter(Boolean).length
  // El pas ACTUAL és el primer que falta; la graduació queda BLOQUEJADA sense talles (no es pot
  // graduar el que no té escala).
  const actual = !pecaFeta ? 2 : (!tallesFetes ? 3 : (!gradFeta ? 4 : null))
  const estatDe = (n) => {
    if (obert === n) return 'ara'
    if (n === 4 && !tallesFetes) return 'blocat'
    if (n === 2 && pecaFeta) return 'fet'
    if (n === 3 && tallesFetes) return 'fet'
    if (n === 4 && gradFeta) return 'fet'
    return obert == null && actual === n ? 'ara' : 'pendent'
  }

  // `enviar` és opcional i existeix per a UN cas: la graduació, que no pot cridar l'endpoint pelat
  // perquè abans ha de passar per les confirmacions de `useConfirmacioRuleset`. La resta del
  // tancament —tancar el subespai, dir-ho, rellegir el model— és idèntica per als tres passos i
  // per això segueix vivint aquí i no es copia a cap d'ells.
  const desa = useCallback(async (payload, okKey, enviar) => {
    try {
      await (enviar ? enviar(payload) : models.updateStep2(id, payload))
      setObert(null)
      setFeedback({ type: 'ok', text: t(okKey) })
      onUpdated?.()
      return true
    } catch (e) {
      // UN 409 QUE ARRIBA FINS AQUÍ ÉS UNA CONFIRMACIÓ DECLINADA, NO UNA AVARIA. L'embolcall ha
      // preguntat, l'usuari ha dit que no, i rellança l'avís tal com venia. Pintar-lo de vermell
      // diria que ha fallat una cosa que precisament NO s'ha arribat a intentar. El subespai es
      // queda obert i amb la tria a la mà, que és on l'usuari l'ha deixada.
      if (e?.response?.status === 409 && e.response.data?.conflict) return false
      const d = e?.response?.data
      setFeedback({ type: 'err', text: d?.message || d?.error || t('resum_wizard.save_error') })
      return false
    }
  }, [id, onUpdated, t])

  // Es rellegeix quan el model canvia: un desat de talles pot moure el valor EFECTIU d'una
  // peça que l'hereta, i el contracte només el resol al servidor. I es rellegeix també a cada
  // escriptura de peça (`versio`): el POST torna la peça creada, però el que la pantalla pinta
  // és LA LLISTA —amb la mare sintètica al davant— i qui la sap fer és el servidor.
  const [versio, setVersio] = useState(0)
  const recarregaPeces = useCallback(() => setVersio(v => v + 1), [])
  useEffect(() => {
    if (!id) return undefined
    let viu = true
    models.peces(id)
      .then(r => { if (viu) setPeces(r.data?.peces || []) })
      // Una llista buida no és cap avaria visible: sense peces, la definició es pinta com
      // sempre s'ha pintat. El que no pot passar és que la pantalla peti per això.
      .catch(() => { if (viu) setPeces([]) })
    return () => { viu = false }
  }, [id, model, versio])

  // L'ANCLA HA DE FER SCROLL, i no ho fa sola. El llapis del contenidor de peça (Mesures,
  // Escalat, Graduació) porta aquí amb `#peca-<codi>`, però React Router NO desplaça a cap ancla:
  // canvia la ruta i prou. I encara que ho fes, arribaria massa aviat — la targeta no existeix
  // fins que `/peces/` ha contestat. Per això el desplaçament penja de `peces` i no del muntatge.
  useEffect(() => {
    if (!peces.length) return
    const ancla = (window.location.hash || '').replace('#', '')
    if (!ancla.startsWith('peca-')) return
    // El `scrollMarginTop` de la targeta ja separa del caire; aquí només cal portar-hi la vista.
    document.getElementById(ancla)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [peces])

  // EL BATEIG DE TOTES LES TARGETES, INCLOSA LA MARE — i són dues portes, no una. La mare no té
  // fila (D3): el seu nom és el `nom_prenda` del MODEL i s'escriu allà on sempre s'ha escrit.
  // Una peça té la seva. Qui pinta la targeta no ha de saber quina de les dues és, i per això la
  // tria es fa aquí i no al contenidor.
  const desaNom = useCallback(async (peca, nou) => {
    try {
      if (peca.es_mare) {
        await models.update(id, { nom_prenda: nou })
        onUpdated?.()          // el nom de la mare viu al model: qui el rellegeix és la fitxa
      } else {
        await models.actualitzarPeca(id, peca.id, { nom: nou })
        recarregaPeces()
      }
      setFeedback({ type: 'ok', text: t('resum_wizard.piece_renamed') })
      return true
    } catch (e) {
      setFeedback({ type: 'err', text: missatgeError(e, t) })
      return false
    }
  }, [id, onUpdated, recarregaPeces, t])

  if (!model) return null

  return (
    <>
      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />
      {/* §8f · DOS CONTENIDORS COSTAT A COSTAT, 1fr/1fr, que s'apilen al breakpoint de 1180. */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 520px), 1fr))',
        gap: 16, alignItems: 'start',
      }}>
        <Informacio model={model} editant={editantInfo} setEditant={setEditantInfo}
          definicioCompleta={fets === 3} onDesat={() => { setEditantInfo(false); onUpdated?.() }}
          onError={(text) => setFeedback({ type: 'err', text })} />

        {/* SET-2/T7-B1 · UN CONTENIDOR PER PRENDA, apilats. La mare hi és la primera i és
            SINTÈTICA: no té fila (D3), i el mateix endpoint que serveix les peces la serveix a
            ella amb els valors del model. Amb un model d'una sola prenda —el 100% del corpus
            d'avui— això és exactament un contenidor, i la pantalla és la d'abans amb la
            capçalera de la peça al davant. */}
        <div style={{ display: 'grid', gap: 16 }}>
          {peces.map(peca => (
            <PecaDefinicioContenidor key={peca.codi || 'base'} peca={peca} fet={fets === 3}
              onDesarNom={nou => desaNom(peca, nou)}
              // La mare no en porta: no té fila i el que s'esborraria seria el model.
              onEsborrar={peca.es_mare ? undefined : () => setAEsborrar(peca)}>
              {peca.es_mare ? (
                <>
                  <PasPeca model={model} estat={estatDe(2)} onObrir={() => setObert(2)}
                    catTargets={catTargets} catConstructions={catConstructions} catFits={catFits}
                    desa={desa} onCancel={() => setObert(null)} />
                  <PasTalles model={model} estat={estatDe(3)} onObrir={() => setObert(3)}
                    desa={desa} onCancel={() => setObert(null)} />
                  <PasGraduacio model={model} estat={estatDe(4)} onObrir={() => setObert(4)}
                    desa={desa} onCancel={() => setObert(null)} />
                </>
              ) : (
                <FilesDeLaPeca model={model} peca={peca}
                  onDesat={okKey => { recarregaPeces(); setFeedback({ type: 'ok', text: t(okKey) }) }}
                  onError={text => setFeedback({ type: 'err', text })} />
              )}
            </PecaDefinicioContenidor>
          ))}

          {/* SET-2/T7-B3 · LA PORTA D'ENTRADA D'UNA PRENDA NOVA. Va AL FINAL de la pila i no a la
              capçalera del contenidor: la llista de peces es llegeix de dalt a baix i el lloc on
              se n'afegeix una és allà on acabaria. */}
          <AfegirPeca modelId={id} peces={peces} onCreada={recarregaPeces}
            onFeedback={setFeedback} />
        </div>
      </div>

      {aEsborrar && (
        <EsborrarPecaDialeg modelId={id} peca={aEsborrar}
          onTancar={() => setAEsborrar(null)}
          onEsborrada={() => {
            setAEsborrar(null)
            recarregaPeces()
            setFeedback({ type: 'ok', text: t('resum_wizard.piece_deleted') })
          }} />
      )}
    </>
  )
}

// ── LA PORTA D'ENTRADA D'UNA PRENDA (SET-2/T7-B3) ─────────────────────────────────────────
//
// Fantasma en repòs —filet discontinu, sense fons—, formulari en obrir-se. El gest mínim és
// escriure el nom i prémer: el CODI ve proposat (`seguentCodiDePeca`) perquè és el que la casa
// numera i no el que el tècnic tria, i el FOCUS va al nom, que és el que sí que ha de dir.
//
// ⚠️ EL CODI PROPOSAT ÉS UNA PROPOSTA I NO UNA RESERVA, i per això el camp queda editable i els
// dos errors del contracte es mostren tal com arriben: `409 garment_duplicat` (dues pestanyes
// obertes n'han proposat el mateix) i `400 garment_mare_no_te_fila` (s'ha buidat el camp — la
// mare és el model i no té fila, D3). Cap dels dos es pot evitar validant al client: el segon
// sí, però amagar-lo faria creure que el camp és opcional.
function AfegirPeca({ modelId, peces, onCreada, onFeedback }) {
  const { t } = useTranslation()
  const [obert, setObert] = useState(false)
  const [codi, setCodi] = useState('')
  const [nom, setNom] = useState('')
  const [desant, setDesant] = useState(false)
  const [error, setError] = useState(null)
  const refNom = useRef(null)

  const obre = () => {
    setCodi(seguentCodiDePeca(peces))
    setNom('')
    setError(null)
    setObert(true)
  }
  useEffect(() => { if (obert) refNom.current?.focus() }, [obert])

  const crea = async () => {
    if (desant) return
    setDesant(true)
    setError(null)
    try {
      // `ordre` va darrere de l'última: la pila es llegeix en l'ordre en què s'ha construït.
      await models.crearPeca(modelId, {
        codi: codi.trim(), nom: nom.trim(), ordre: peces.filter(p => !p.es_mare).length + 1,
      })
      setObert(false)
      onCreada()
      onFeedback({ type: 'ok', text: t('resum_wizard.piece_created') })
    } catch (e) {
      // L'error es queda DINS de la targeta, al costat del camp que l'ha provocat: el formulari
      // segueix obert i amb el que s'havia escrit, que és on l'usuari l'ha deixat.
      setError(missatgeError(e, t))
    } finally { setDesant(false) }
  }

  if (!obert) {
    return (
      <button type="button" onClick={obre} style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        padding: '14px 16px', width: '100%',
        background: 'none', borderWidth: 1, borderStyle: 'dashed', borderColor: 'var(--line)',
        borderRadius: 'var(--r-card)', cursor: 'pointer',
        fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)',
      }}>
        <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 14 }} />
        {t('resum_wizard.add_piece')}
      </button>
    )
  }

  return (
    <section style={{
      background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid',
      borderColor: 'var(--gold-border)', borderRadius: 'var(--r-card)', padding: '14px 16px',
      fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: '96px 1fr', gap: 10 }}>
        <label style={{ display: 'block' }}>
          <span style={retolCamp}>{t('resum_wizard.piece_code')}</span>
          <input value={codi} onChange={e => setCodi(e.target.value)} disabled={desant}
            style={{ ...camp, marginTop: 4 }} />
        </label>
        <label style={{ display: 'block' }}>
          <span style={retolCamp}>{t('resum_wizard.piece_name')}</span>
          <input ref={refNom} value={nom} onChange={e => setNom(e.target.value)} disabled={desant}
            onKeyDown={e => {
              if (e.key === 'Enter') { e.preventDefault(); crea() }
              if (e.key === 'Escape') { e.preventDefault(); setObert(false) }
            }}
            placeholder={t('resum_wizard.piece_name_ph')}
            style={{ ...camp, marginTop: 4 }} />
        </label>
      </div>
      {error && (
        <p style={{ margin: '10px 0 0', color: 'var(--err)', fontSize: 'var(--fs-caption)' }}>{error}</p>
      )}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
        <Boto variant="ter" onClick={() => setObert(false)}>{t('model_wizard.cancel')}</Boto>
        {/* SECUNDÀRIA: el blau d'aquesta columna és del pas obert (§8f), i afegir una prenda no
            és el pas que completa la definició del model — és una porta al costat. */}
        <Boto variant="sec" onClick={crea} disabled={desant || !codi.trim()}>
          {desant ? t('model_wizard.saving') : t('resum_wizard.add_piece')}
        </Boto>
      </div>
    </section>
  )
}

// ── L'ESBORRAT D'UNA PRENDA (SET-2/T7-B3) ─────────────────────────────────────────────────
//
// 🛑 EL 409 ES MOSTRA TAL COM ARRIBA, amb el desglossament que el payload porta. «No pots» sense
// el motiu obliga qui ho llegeix a endevinar per on buidar la peça, i el servidor ja diu QUANTES
// files i DE QUINA taula. Aquí no es tradueixen els noms de taula: són el vocabulari del domini
// (com els codis POM), i inventar-ne un de pantalla trencaria el pont entre el que es llegeix
// aquí i el que hi ha a la base.
//
// El diàleg NO es tanca amb el 409: es queda obert dient per què no s'ha pogut, perquè un modal
// que desapareix amb un toast vermell fa que el motiu s'hagi de recordar de memòria.
function EsborrarPecaDialeg({ modelId, peca, onTancar, onEsborrada }) {
  const { t } = useTranslation()
  const [bloqueig, setBloqueig] = useState(null)
  const [esborrant, setEsborrant] = useState(false)

  const esborra = async () => {
    if (esborrant) return
    setEsborrant(true)
    try {
      await models.esborrarPeca(modelId, peca.id)
      onEsborrada()
    } catch (e) {
      const d = e?.response?.data
      if (e?.response?.status === 409 && d?.codi === 'garment_amb_dades') setBloqueig(d)
      else setBloqueig({ error: missatgeError(e, t) })
    } finally { setEsborrant(false) }
  }

  const nom = peca.nom || peca.codi
  return (
    <Modal
      title={bloqueig ? t('resum_wizard.delete_piece_blocked') : t('resum_wizard.delete_piece')}
      subtitle={t('resum_wizard.piece_named', { peca: nom })}
      // AMB EL BLOQUEIG, EL PRIMARI SEGUEIX SENT ESBORRAR, i és una acció de debò: qui buida la
      // peça en una altra pestanya ha de poder tornar-hi sense reobrir el diàleg. Dos botons que
      // fessin tots dos el mateix (tancar) serien una tria falsa.
      confirmLabel={esborrant ? t('model_wizard.saving') : t('resum_wizard.delete_piece')}
      cancelLabel={bloqueig ? t('app.close') : t('model_wizard.cancel')}
      confirmDisabled={esborrant}
      onCancel={onTancar} onConfirm={esborra}>
      {bloqueig ? (
        <>
          <p style={{ fontSize: 'var(--fs-body)', marginBottom: 12 }}>{bloqueig.error}</p>
          {bloqueig.penjades && (
            <div style={{
              borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
              borderRadius: 8, padding: '10px 12px', fontSize: 'var(--fs-body)',
            }}>
              {Object.entries(bloqueig.penjades).sort(([a], [b]) => a.localeCompare(b)).map(([taula, n]) => (
                <div key={taula} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontFamily: MONO }}>{taula}</span><strong>{n}</strong>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <p style={{ fontSize: 'var(--fs-body)', margin: 0 }}>{t('resum_wizard.delete_piece_warn')}</p>
      )}
    </Modal>
  )
}

// ── LES FILES D'UNA PEÇA QUE NO ÉS LA MARE ────────────────────────────────────────────────
//
// Es pinta el que el CONTRACTE serveix, i res més. `CAMPS_HERETABLES` són quatre —sistema, joc
// de regles, run i talla base—, o sigui que una peça té fila de TALLES i de GRADUACIÓ.
//
// LA FILA DE «PEÇA» HI ÉS, I NO ÉS UNA FILA HERETADA (decisió d'Agus, 11/08). L'ull del tècnic
// busca les tres files iguals a totes les targetes, i una targeta que no diu QUÈ ÉS la peça no
// li serveix encara que no ho pugui canviar. Però el contracte NEGA que els eixos i el
// `garment_type_item` baixin a la prenda (`ElGarmentTypeItemNoHiEsTest` ho fixa), o sigui que
// això NO és herència: és informació DEL MODEL a títol de context, amb el seu propi origen
// (`ORIGEN.DEL_MODEL`) i sense «Canviar». Dir-ne «hereta» prometria una porta d'edició que no
// ha d'arribar mai — la distinció la guarda el banc de `pecaDefinicio`.
//
// EL «CANVIAR» JA ÉS VIU (SET-2/T7-B3): la porta d'escriptura existeix i desa amb un PATCH que
// parla NOMÉS del que s'ha tocat.
//
// 🔑 I «TORNA A HERETAR» ÉS UN `null` EXPLÍCIT, no un camp absent. La distinció és del contracte
// («`null` vol dir torna a heretar; el camp ABSENT vol dir no toquis») i sense ella desheretar
// seria un camí d'anada sense tornada. Per això aquest component no construeix mai un payload
// sencer amb el que la peça té: envia el que l'usuari ha mogut, i prou.
function FilesDeLaPeca({ model, peca, onDesat, onError }) {
  const { t } = useTranslation()
  const cap = t('resum_wizard.no_value')
  const gt = [model.garment_type_nom, model.garment_type_item_nom].filter(Boolean).join(' · ')
  // Quin editor està obert dins d'AQUESTA targeta. És estat local de la peça i no del Resum:
  // dues targetes obertes alhora són dues edicions independents, com dues peces són dues peces.
  const [obert, setObert] = useState(null)

  const desa = async (dades, okKey) => {
    try {
      await models.actualitzarPeca(model.id, peca.id, dades)
      setObert(null)
      onDesat(okKey)
      return true
    } catch (e) {
      // El 400 de `talles_desconegudes` ve de la PORTA ÚNICA del model (S24b): la peça es
      // comporta exactament com el model i el missatge és el mateix. No es reinterpreta.
      onError(missatgeError(e, t))
      return false
    }
  }

  // Declara = el contracte diu `heretat: false` en algun dels camps del grup. La fila de talles
  // n'agrupa tres, i tornar a heretar-la els ha de buidar tots tres: deixar-ne un de declarat
  // faria una peça que hereta el run però no el sistema, que és un estat que ningú ha demanat.
  const declaraTalles = [peca.size_system, peca.size_run_model, peca.base_size_label]
    .some(c => c && c.heretat === false)
  const declaraGraduacio = peca.grading_rule_set?.heretat === false

  const heretaDeNou = (camps, okKey) => desa(
    Object.fromEntries(camps.map(c => [c, null])), okKey)

  return (
    <>
      {/* Fixa, apagada i sense acció: la peça no pot canviar això mai. Tot en UNA línia, com les
          altres dues: els eixos i el tipus de peça separats per punt volat. */}
      <FilaDefinicio etiqueta={t('resum_wizard.step_piece')} origen={ORIGEN.DEL_MODEL}>
        <span>
          {[model.target && t(`model_wizard.target_${model.target}`, model.target),
            model.construction && t(`model_wizard.construction_${model.construction}`, model.construction),
            model.fit_type && t(`model_wizard.fit_${model.fit_type}`, model.fit_type),
            gt || null]
            .filter(Boolean).join(' · ')}
        </span>
      </FilaDefinicio>

      <FilaDefinicio etiqueta={t('resum_wizard.step_sizes')}
        origen={origenDeLaFila(peca.size_run_model)}
        expandit={obert === 'talles'}
        accio={obert === 'talles' ? null : (
          <BotoCanviar onClick={() => setObert('talles')}>{t('resum_wizard.change')}</BotoCanviar>
        )}>
        {obert === 'talles' ? (
          <EditorTalles model={model}
            // Es parteix dels valors EFECTIUS: s'edita des del que governa ara, heretat o no.
            inicial={{ size_system_id: peca.size_system?.valor ?? null,
              size_run_model: peca.size_run_model?.valor ?? '',
              base_size_label: peca.base_size_label?.valor ?? null }}
            onDesar={p => desa({ size_system: p.size_system_id, size_run_model: p.size_run,
              base_size_label: p.base_size }, 'resum_wizard.sizes_saved')}
            onCancel={() => setObert(null)}
            extra={declaraTalles ? (
              <Boto variant="ter" onClick={() => heretaDeNou(
                ['size_system', 'size_run_model', 'base_size_label'], 'resum_wizard.inherits_again')}>
                {t('resum_wizard.inherit_again')}
              </Boto>
            ) : null} />
        ) : (
          // Sistema, run i talla base EN UNA LÍNIA — la mateixa lectura que la fila de la mare,
          // que és el que fa que les tres files es puguin comparar entre targetes d'un cop d'ull.
          <>
            <ValorCamp camp={peca.size_system} buit={cap} />
            <ValorCamp camp={peca.size_run_model} buit={cap} />
            {peca.base_size_label?.etiqueta
              ? <span style={{ color: 'var(--text-soft)' }}>
                  {peca.base_size_label.etiqueta} · {t('resum_wizard.base')}
                </span>
              : null}
          </>
        )}
      </FilaDefinicio>

      <FilaDefinicio etiqueta={t('resum_wizard.step_grading')}
        origen={origenDeLaFila(peca.grading_rule_set)}
        expandit={obert === 'graduacio'}
        accio={obert === 'graduacio' ? null : (
          <BotoCanviar onClick={() => setObert('graduacio')}>{t('resum_wizard.change')}</BotoCanviar>
        )}>
        {obert === 'graduacio' ? (
          <EditorGraduacio model={model} inicialId={peca.grading_rule_set?.valor ?? null}
            // El PATCH d'una peça NO passa per `useConfirmacioRuleset`: aquesta porta no valida
            // el joc ni esborra regles residents —`actualitza_peca` només mou el FK— i per tant
            // no emet cap dels 409 que aquell hook confirma. Embolcallar-lo hi prometria una
            // pregunta que no arribarà mai.
            onDesar={id => desa({ grading_rule_set: id }, 'resum_wizard.grading_saved')}
            onCancel={() => setObert(null)}
            extra={declaraGraduacio ? (
              <Boto variant="ter" onClick={() => heretaDeNou(['grading_rule_set'],
                'resum_wizard.inherits_again')}>
                {t('resum_wizard.inherit_again')}
              </Boto>
            ) : null} />
        ) : (
          <ValorCamp camp={peca.grading_rule_set} buit={cap} />
        )}
      </FilaDefinicio>
    </>
  )
}

// ── ESQUERRA · PAS 1 · IDENTIFICACIÓ ──────────────────────────────────────────────────────
function Informacio({ model, editant, setEditant, definicioCompleta, onDesat, onError }) {
  const { t, i18n } = useTranslation()
  const dateLocale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'
  const [form, setForm] = useState(null)
  const [desant, setDesant] = useState(false)

  const obre = () => {
    setForm({
      customer: model.customer ?? null,
      codi_client: model.codi_client === model.codi_intern ? '' : (model.codi_client || ''),
      collection: model.collection || '',
      nom_prenda: model.nom_prenda || '',
      descripcio: model.descripcio || '',
      data_objectiu: model.data_objectiu || '',
    })
    setEditant(true)
  }

  const desa = async () => {
    setDesant(true)
    try {
      // El PATCH del model és el de sempre (`models.update`): aquest formulari és el pas 1 del
      // wizard, i el pas 1 sempre ha escrit aquí. `data_objectiu` buit = sense deadline (null),
      // que NO és el mateix que «no el toquis».
      await models.update(model.id, {
        customer: form.customer,
        codi_client: form.codi_client || model.codi_intern,
        collection: form.collection,
        nom_prenda: form.nom_prenda,
        descripcio: form.descripcio,
        data_objectiu: form.data_objectiu || null,
      })
      onDesat()
    } catch (e) {
      onError(e?.response?.data?.detail || t('resum_wizard.save_error'))
    } finally { setDesant(false) }
  }

  const buit = (v, txt) => (v ? v : <span style={buitText}>{txt}</span>)

  return (
    <Targeta
      titol={t('resum_wizard.information')}
      nota={t('resum_wizard.step1')}
      accions={!editant && (
        // §8f · EL BLAU DEPÈN DE L'ESTAT: mentre la definició no està completa, dir qui és el
        // model és el que toca fer, i «Editar» és l'acció primària. Quan ja ho està, baixa a
        // secundària — el blau se'n va al pas que queda pendent, a la columna de la dreta.
        <Boto variant={definicioCompleta ? 'sec' : 'pri'} onClick={obre}>
          <i className="ti ti-edit" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
          {t('app.edit')}
        </Boto>
      )}>
      {editant ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label style={{ display: 'block' }}>
            <span style={retolCamp}>{t('model_wizard.customer')}</span>
            <div style={{ marginTop: 4 }}>
              <CustomerSelector value={form.customer} onChange={v => setForm(f => ({ ...f, customer: v }))}
                allowCreate={false} onError={onError} />
            </div>
          </label>
          {[
            ['codi_client', t('model_wizard.ref_client')],
            ['collection', t('model_wizard.collection')],
            ['nom_prenda', t('model_wizard.nom_prenda')],
          ].map(([k, label]) => (
            <label key={k} style={{ display: 'block' }}>
              <span style={retolCamp}>{label}</span>
              <input value={form[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))}
                style={{ ...camp, marginTop: 4 }} />
            </label>
          ))}
          <label style={{ display: 'block' }}>
            <span style={retolCamp}>{t('model_wizard.descripcio')}</span>
            <textarea value={form.descripcio} onChange={e => setForm(f => ({ ...f, descripcio: e.target.value }))}
              style={{ ...camp, marginTop: 4, minHeight: 70, resize: 'vertical' }} />
          </label>
          <label style={{ display: 'block' }}>
            <span style={retolCamp}>{t('model_wizard.deadline_optional')}</span>
            <input type="date" value={form.data_objectiu}
              onChange={e => setForm(f => ({ ...f, data_objectiu: e.target.value }))}
              style={{ ...camp, marginTop: 4 }} />
          </label>
          {/* L'ANY I LA TEMPORADA NO S'EDITEN AQUÍ, i no és un oblit: manen el `codi_intern` i
              la seqüència del client, i el wizard ja els bloqueja en edició (`disabled={isEditMode}`).
              Canviar-los seria rebatejar el model, que és una altra conversa. */}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', paddingTop: 4 }}>
            <Boto variant="ter" onClick={() => setEditant(false)}>{t('model_wizard.cancel')}</Boto>
            <Boto variant="pri" onClick={desa} disabled={desant}>
              {desant ? t('model_wizard.saving') : t('model_wizard.save')}
            </Boto>
          </div>
        </div>
      ) : (
        <div>
          <Fila etiqueta={t('model_wizard.customer')}>{buit(model.customer_nom, t('resum_wizard.no_customer'))}</Fila>
          <Fila etiqueta={t('model_wizard.internal_ref')}>{model.codi_intern}</Fila>
          <Fila etiqueta={t('model_wizard.ref_client')}>
            {buit(model.codi_client !== model.codi_intern ? model.codi_client : '', t('resum_wizard.no_value'))}
          </Fila>
          <Fila etiqueta={t('resum_wizard.year_season')}>
            {model.any} · {model.temporada}{' '}
            <span style={{ color: 'var(--text-soft)' }}>{t(`model_wizard.season_${model.temporada}`, '')}</span>
          </Fila>
          <Fila etiqueta={t('model_wizard.collection')}>{buit(model.collection, t('resum_wizard.no_value'))}</Fila>
          <Fila etiqueta={t('model_wizard.nom_prenda')}>{buit(model.nom_prenda, t('resum_wizard.no_value'))}</Fila>
          <Fila etiqueta={t('model_wizard.descripcio')}>{buit(model.descripcio, t('resum_wizard.no_value'))}</Fila>
          <Fila etiqueta={t('model_wizard.deadline_optional')}>
            {model.data_objectiu
              ? new Date(model.data_objectiu).toLocaleDateString(dateLocale)
              : <span style={buitText}>{t('resum_wizard.no_deadline')}</span>}
          </Fila>
          <Fila etiqueta={t('resum_wizard.created_by')}>
            {model.created_by_nom || <span style={buitText}>{t('resum_wizard.no_value')}</span>}
            {model.created_at && ` · ${new Date(model.created_at).toLocaleDateString(dateLocale)}`}
          </Fila>
        </div>
      )}
    </Targeta>
  )
}

// ── DRETA · PAS 2 · PEÇA ──────────────────────────────────────────────────────────────────
function PasPeca({ model, estat, onObrir, catTargets, catConstructions, catFits, desa, onCancel }) {
  const { t } = useTranslation()
  const obert = estat === 'ara'
  const [target, setTarget] = useState(model.target || null)
  const [construction, setConstruction] = useState(model.construction || null)
  const [fit, setFit] = useState(model.fit_type || null)
  const [pick, setPick] = useState({})
  const [item, setItem] = useState(null)
  const [desant, setDesant] = useState(false)

  // En obrir el subespai, l'estat parteix SEMPRE del que el model té desat: un formulari que
  // recorda el que hi havia dues obertures enrere és un formulari que menteix.
  useEffect(() => {
    if (!obert) return
    setTarget(model.target || null)
    setConstruction(model.construction || null)
    setFit(model.fit_type || null)
    setItem(null)
    setPick({})
  }, [obert, model.target, model.construction, model.fit_type])

  const finderValue = 'garmentTypeId' in pick ? pick : {
    garmentGroup: model.garment_type_grup ?? null,
    garmentTypeId: model.garment_type ?? null,
    garmentTypeItemId: model.garment_type_item ?? null,
  }

  const desar = async () => {
    setDesant(true)
    const ok = await desa({
      target: target || undefined,
      construction: construction || undefined,
      garment_type_item_id: item?.id || model.garment_type_item || undefined,
    }, 'resum_wizard.piece_saved')
    setDesant(false)
    if (!ok) return
  }

  if (!obert) {
    return (
      <FilaDefinicio etiqueta={t('resum_wizard.step_piece')}
        accio={estat === 'fet'
          ? <BotoCanviar onClick={onObrir}>{t('resum_wizard.change')}</BotoCanviar>
          : null}>
        {estat === 'fet' && (
          // ELECCIONS FIXADES I VISIBLES (§8f): els tres eixos en chips verds d'inclusió i el
          // tipus de peça escrit. Res s'amaga en tancar-se — però tot va EN UNA FILA, i els
          // sub-rètols («Target · Construcció · Fit», «Tipus de peça») se'n van: un chip verd ja
          // diu què és, i el rètol PEÇA de l'esquerra ja diu de quin apartat parlem.
          <>
            {model.target && <Xip marcat disabled>{t(`model_wizard.target_${model.target}`, model.target)}</Xip>}
            {model.construction && <Xip marcat disabled>{t(`model_wizard.construction_${model.construction}`, model.construction)}</Xip>}
            {model.fit_type && <Xip marcat disabled>{t(`model_wizard.fit_${model.fit_type}`, model.fit_type)}</Xip>}
            <span>
              <b>{model.garment_type_nom}</b>
              {model.garment_type_item_nom && ` · ${model.garment_type_item_nom}`}
            </span>
          </>
        )}
      </FilaDefinicio>
    )
  }

  return (
    <Subespai num={2} titol={t('resum_wizard.step_piece')} estat="ara">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <EixFila etiqueta={t('model_wizard.axis_target')} opcions={catTargets} valor={target}
          onTria={setTarget} tradueix={(c, n) => t(`model_wizard.target_${c}`, n)} t={t} />
        <EixFila etiqueta={t('model_wizard.axis_construction')} opcions={catConstructions} valor={construction}
          onTria={setConstruction} tradueix={(c, n) => t(`model_wizard.construction_${c}`, n)} t={t} />
        <EixFila etiqueta={t('model_wizard.axis_fit')} opcions={catFits} valor={fit}
          onTria={setFit} tradueix={(c, n) => t(`model_wizard.fit_${c}`, n)} t={t} />
        {/* EL NAVEGADOR DE PECES ÉS EL MATEIX COMPONENT que el pas 2 del wizard (`CascadeFinder`):
            la maqueta ho diu amb totes les lletres —«els selectors de dins són els que ja hi ha»—
            i duplicar-lo seria estrenar una segona manera de triar una peça. */}
        <div>
          <span style={retolCamp}>{t('model_wizard.garment')}</span>
          <div style={{ marginTop: 4 }}>
            <CascadeFinder
              target={target}
              compat={{ construction, fit }}
              value={finderValue}
              onChange={setPick}
              onPickItem={({ item: it }) => setItem(it)}
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', paddingTop: 4 }}>
          <Boto variant="ter" onClick={onCancel}>{t('model_wizard.cancel')}</Boto>
          {/* EL SEU DESAR ÉS L'ÚNIC BLAU d'aquesta columna (§8f). */}
          <Boto variant="pri" onClick={desar} disabled={desant || !(item?.id || model.garment_type_item)}>
            {desant ? t('model_wizard.saving') : t('resum_wizard.save_piece')}
          </Boto>
        </div>
      </div>
    </Subespai>
  )
}

// Una fila d'eix (target · construcció · fit). Re-clicar DESMARCA: el buit d'un eix és una
// resposta possible, i no poder-hi tornar seria una porta d'un sol sentit.
function EixFila({ etiqueta, opcions, valor, onTria, tradueix }) {
  return (
    <div>
      <span style={retolCamp}>{etiqueta}</span>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
        {(opcions || []).map(o => (
          <Xip key={o.codi} marcat={valor === o.codi}
            onClick={() => onTria(valor === o.codi ? null : o.codi)}>
            {tradueix(o.codi, o.nom_en)}
          </Xip>
        ))}
      </div>
    </div>
  )
}

// ── L'EDITOR DE TALLES, COMPARTIT PER LA MARE I PER QUALSEVOL PRENDA (SET-2/T7-B3) ────────
//
// Era el cos del pas 3 i prou. Des que una peça pot declarar les seves talles, el MATEIX gest
// existeix a dues alçades —el model i la prenda— i el que canvia no és la tria: és ON es desa.
// Per això surt d'aquí un component i no una segona còpia. La llei de la casa és explícita
// («no més pedaços: unificar el ja construït»), i duplicar-lo hauria estrenat una segona manera
// de triar un run el mateix dia que la primera va aprendre a viure dins d'una peça.
//
// ES MUNTA NOMÉS QUAN S'OBRE, i això és el que abans feia un `if (!obert)` dins de cada efecte:
// muntar = obrir vol dir que l'estat neix del que hi ha desat cada vegada, i un formulari que
// recorda el que hi havia dues obertures enrere és un formulari que menteix.
//
// `inicial` són els valors DE PARTIDA, i per a una peça són els EFECTIUS (el que governa ara,
// heretat o no): s'edita des del que es veu, no des d'un buit que amagaria el que mana.
function EditorTalles({ model, inicial, onDesar, onCancel, extra }) {
  const { t } = useTranslation()
  const [systems, setSystems] = useState([])
  const [sel, setSel] = useState(null)
  const [run, setRun] = useState([])
  const [base, setBase] = useState(null)
  const [desant, setDesant] = useState(false)

  // EL CODI DEL CLIENT del model. El detall no el porta (només `customer_nom`) i la
  // proximitat el necessita: sense ell, el run DEL CLIENT d'aquest model no pot anar primer i
  // la llista queda ordenada com si el model no fos de ningú (el parany del model 174).
  //
  // SET-2/T7-B5 — I NOMÉS AMB L'EDITOR OBERT. Aquest codi només serveix per ORDENAR els runs
  // candidats en el moment de triar-ne un: amb el pas tancat no hi ha cap llista a ordenar, i la
  // crida es feia igualment a cada fitxa de model que s'obria. El pas tancat pinta el run que ja
  // hi ha, que ve al detall i no necessita ningú. Muntar-se en obrir ho garanteix per construcció.
  const [codiClient, setCodiClient] = useState(null)
  useEffect(() => {
    if (!model.customer) { setCodiClient(null); return undefined }
    let viu = true
    customers.get(model.customer)
      .then(r => { if (viu) setCodiClient(r.data?.codi ?? null) })
      .catch(() => { if (viu) setCodiClient(null) })
    return () => { viu = false }
  }, [model.customer, model.grading_rule_set])

  // Triar un sistema NO substitueix el run en silenci: si el que hi ha desat hi cap, es
  // conserva (i amb ell la talla base). És la mateixa llei F1.2 del wizard.
  const triaSistema = (s, rehidratant = false) => {
    setSel(s)
    const labels = labelsOf(s)
    const desat = (inicial.size_run_model || '').split(/[·,;]/).map(x => x.trim()).filter(Boolean)
    const conserva = rehidratant && desat.length && desat.every(l => labels.includes(l))
    const nou = conserva ? desat : labels
    setRun(nou)
    setBase(conserva && inicial.base_size_label && nou.includes(inicial.base_size_label)
      ? inicial.base_size_label
      : (nou[Math.floor(nou.length / 2)] || nou[0] || null))
  }

  // Els sistemes s'ORDENEN PER PROXIMITAT i NO S'AMAGA CAP (D-31.3 · `utils/proximitatRun`,
  // el mateix mòdul que el pas 3 del wizard). El run del client d'aquest model, primer.
  //
  // ELS EIXOS DE L'ORDRE SÓN ELS DEL MODEL fins i tot editant una peça, i no és un descuit: el
  // contracte NEGA que els eixos i el `garment_type_item` baixin a la prenda
  // (`ElGarmentTypeItemNoHiEsTest`). La peça no en té de propis dels quals ordenar.
  useEffect(() => {
    let viu = true
    sizeSystems.list({ actiu: true, page_size: 100 })
      .then(r => {
        if (!viu) return
        const rows = ordenaPerProximitat(
          (r.data?.results ?? r.data ?? []).filter(s => (s.talles || []).length > 0),
          { target: model.target, construction: model.construction, fit: model.fit_type,
            grup: model.garment_type_grup },
          codiClient)
        setSystems(rows)
        const seu = rows.find(s => s.id === inicial.size_system_id)
        if (seu) triaSistema(seu, true)
      })
      .catch(() => { if (viu) setSystems([]) })
    return () => { viu = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inicial.size_system_id, codiClient])

  const toggleTalla = (label) => setRun(prev => (
    prev.includes(label) ? prev.filter(x => x !== label) : ordenaPelSistema([...prev, label], labelsOf(sel))
  ))

  const valid = !!(sel && run.length > 0 && base && run.includes(base))
  const desar = async () => {
    setDesant(true)
    await onDesar({ size_system_id: sel.id, size_run: run.join('·'), base_size: base })
    setDesant(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <span style={retolCamp}>
          {model.target
            ? t('resum_wizard.systems_for', { target: t(`model_wizard.target_${model.target}`, model.target) })
            : t('model_wizard.size_systems_label')}
        </span>
        {/* ORDENA, MAI AMAGA (D-31.3): hi són TOTS, i el que fa el `maxHeight` és no menjar-se
            la pàgina amb vint runs — desplaçar-se no és ocultar. */}
        <div style={{ marginTop: 4, maxHeight: 320, overflowY: 'auto' }}>
          {systems.length === 0 && <span style={buitText}>{t('model_wizard.no_sizes')}</span>}
          {systems.map(s => (
            <FilaRun key={s.id} sistema={s} triat={sel?.id === s.id} onTria={() => triaSistema(s)} t={t} />
          ))}
        </div>
      </div>
      {sel && (
        <div>
          <span style={retolCamp}>{t('resum_wizard.run_and_base')}</span>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
            {labelsOf(sel).map(l => (
              <Xip key={l} marcat={run.includes(l)} onClick={() => toggleTalla(l)}>{l}</Xip>
            ))}
          </div>
          {run.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <span style={retolCamp}>{t('model_wizard.base_size')}</span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                {run.map(l => (
                  <Xip key={l} marcat={base === l} onClick={() => setBase(l)}>
                    {l}{base === l ? ` · ${t('resum_wizard.base')}` : ''}
                  </Xip>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center', paddingTop: 4 }}>
        {!valid && <span style={{ ...buitText, fontSize: 'var(--fs-caption)' }}>{t('resum_wizard.need_base')}</span>}
        {extra}
        <Boto variant="ter" onClick={onCancel}>{t('model_wizard.cancel')}</Boto>
        <Boto variant="pri" onClick={desar} disabled={desant || !valid}>
          {desant ? t('model_wizard.saving') : t('resum_wizard.save_sizes')}
        </Boto>
      </div>
    </div>
  )
}

// ── DRETA · PAS 3 · TALLES ────────────────────────────────────────────────────────────────
function PasTalles({ model, estat, onObrir, desa, onCancel }) {
  const { t } = useTranslation()
  const obert = estat === 'ara'

  if (!obert) {
    return (
      <FilaDefinicio etiqueta={t('resum_wizard.step_sizes')}
        accio={estat === 'fet'
          ? <BotoCanviar onClick={onObrir}>{t('resum_wizard.change')}</BotoCanviar>
          : null}>
        {estat === 'fet' && (
          // El sistema i les pastilles del run, EN UNA FILA. La talla base segueix marcada dins
          // de la seva pastilla —és l'única de les cinc que porta text— i per això el run no
          // necessita cap rètol que digui quina és.
          <>
            <b>{model.size_system_nom || model.size_system_codi}</b>
            {(model.size_run_model || '').split('·').filter(Boolean).map(l => (
              <Xip key={l} marcat={l === model.base_size_label} disabled>
                {l}{l === model.base_size_label ? ` · ${t('resum_wizard.base')}` : ''}
              </Xip>
            ))}
          </>
        )}
      </FilaDefinicio>
    )
  }

  return (
    <Subespai num={3} titol={t('resum_wizard.step_sizes')} estat="ara">
      <EditorTalles model={model}
        inicial={{ size_system_id: model.size_system, size_run_model: model.size_run_model,
          base_size_label: model.base_size_label }}
        onDesar={p => desa(p, 'resum_wizard.sizes_saved')}
        onCancel={onCancel} />
    </Subespai>
  )
}

// La fila d'un run. Triada = VERD (inclusió): triar un sistema és declarar-lo del model.
function FilaRun({ sistema, triat, onTria, t }) {
  const [toc, gestos] = useToc()
  return (
    <div onClick={onTria} {...gestos} style={{
      borderWidth: 1, borderStyle: 'solid',
      borderColor: triat ? 'var(--ok)' : 'var(--line)',
      borderRadius: 'var(--r-ctrl)', padding: '8px 12px', marginBottom: 6, cursor: 'pointer',
      background: triat ? 'var(--ok-bg)' : (toc.hover ? 'var(--sel)' : 'var(--panel)'),
    }}>
      <span style={{ fontWeight: 600 }}>{sistema.nom || sistema.codi}</span>{' '}
      {sistema.customer_codi
        ? <BadgeNeutre casa>{t('model_wizard.client_run')} · {sistema.customer_codi}</BadgeNeutre>
        : <BadgeNeutre>{t('model_wizard.canonical')}</BadgeNeutre>}
      <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>{sistema.codi}</div>
    </div>
  )
}

// ── DRETA · PAS 4 · GRADUACIÓ ─────────────────────────────────────────────────────────────
// §8f — «Graduació segueix blau-per-estat: sense joc = "Definir graduació" primari; amb joc =
// valors fixats + "Canviar"».
//
// ── PER QUÈ AQUÍ HI HAVIA UNA PORTA, I PER QUÈ JA NO N'HI HA (Agus, QA 09/08) ─────────────
// Fins avui aquest pas no editava res: «Definir graduació» feia `navigate('…/editar?block=4')`
// i et deixava al ModelWizard vell. El motiu escrit era que el canvi de joc destrueix regles
// residents i demana un 409 confirmat (D-31.4), i que duplicar aquell gest duplicaria la
// confirmació. **La premissa era falsa**: la confirmació no viu al wizard, viu a
// `useConfirmacioRuleset` —un hook compartit, fet precisament perquè no se n'escrivís una segona
// còpia—, i `update-step2` és el MATEIX endpoint que el wizard crida. O sigui que portar el gest
// aquí no duplica cap confirmació: en reutilitza exactament la mateixa, com fan els passos 2 i 3.
//
// El que sí que era un defecte és el que quedava: els altres dos subespais editen al lloc on
// després es llegeixen, i aquest et treia de la fitxa. Un contenidor que es diu «Definició del
// model» i que en el seu últim pas t'expulsa a una altra pantalla no és un contenidor.
//
// ── LA LLISTA ORDENA, MAI TRIA (LLEI C5 · D-31.3), I PER AIXÒ ÉS `eliminatiu` ─────────────
// El picker va en mode ELIMINATIU, no `strict`, i la diferència no és cosmètica: l'estricte
// exigeix que el joc DECLARI target, construcció, fit, grup i sistema, i que tots cinc casin.
// El catàleg d'aquesta casa no és així —el joc de Brownie (142 regles) porta els eixos BUITS i
// només declara el sistema de talles—, i buit NO vol dir incompatible: vol dir NO DECLARAT
// (llei de N1). Amb `strict` aquest pas no oferiria RES i el model no es podria graduar mai des
// d'aquí. Amb `eliminatiu` hi són tots, els compatibles primer i els altres atenuats i AMB EL
// MOTIU ESCRIT — que és la mateixa llei que el pas 3 aplica als runs.
//
// Els dos casos que el backend sí que bloqueja de debò (joc buit · sistema de talles divergent)
// segueixen sent seus i tornen 400: aquí no es reimplementen, es mostren.
// ── L'EDITOR DE GRADUACIÓ, COMPARTIT PER LA MARE I PER QUALSEVOL PRENDA (SET-2/T7-B3) ─────
//
// Mateix argument que `EditorTalles`: la tria és la mateixa a les dues alçades i el que canvia
// és on es desa. Es munta en obrir, i per això la tria parteix SEMPRE del que hi ha desat.
function EditorGraduacio({ model, inicialId, onDesar, onCancel, extra }) {
  const { t } = useTranslation()
  const [jocs, setJocs] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [sel, setSel] = useState(inicialId)
  const [desant, setDesant] = useState(false)

  // El CATÀLEG només es carrega amb l'editor obert: amb el pas tancat no hi ha res a triar i
  // dues crides per cada fitxa de model serien dues crides per res.
  useEffect(() => {
    let viu = true
    Promise.all([
      // `amb_regles: 1` com al wizard: un joc sense regles no és una opció llunyana, és un
      // bloqueig dur al backend (400 `ruleset_buit`). Oferir-lo seria oferir un carreró sense
      // sortida, que no és el que «no amagar» vol dir.
      // S45/C — I EL CATÀLEG ARRIBA JA ACOTAT. Abans es demanaven els 51 jocs amb regles de
      // PROD —18 d'ells JUBILATS i 24 de LOS— i el picker els pintava tots. El sedàs va al
      // SERVIDOR i no aquí: quatre pantalles filtrant pel seu compte serien quatre filtres
      // que divergeixen. `actiu=True` és ara el defecte del ViewSet (jubilar ≠ amagar: qui
      // els vol, passa `include_inactive=1`), i `per_client` demana els del client del model
      // MÉS els de catàleg —mai els d'un altre client.
        // 🚨 `inclou`: EL JOC QUE EL MODEL JA PORTA NO ES POT AMAGAR MAI. Al 1383 (TRV) hi
        // ha assignat el joc 219, que és de BRW: amb el sedàs de client, el picker s'obriria
        // sense ell i diria que el model no en té cap. El que està EN ÚS travessa el sedàs.
      gradingRuleSets.list({
        page_size: 200, amb_regles: 1,
        ...(model.customer ? { per_client: model.customer } : {}),
        ...(model.grading_rule_set ? { inclou: model.grading_rule_set } : {}),
      }),
      garmentGroups.list({ page_size: 200 }),
    ])
      .then(([rsRes, ggRes]) => {
        if (!viu) return
        const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
        const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
        const map = {}; gg.forEach(g => { map[g.id] = g.codi })
        setJocs(rs); setGgCodiById(map)
      })
      .catch(() => { if (viu) setJocs([]) })
    return () => { viu = false }
  }, [model.customer, model.grading_rule_set])

  // Els eixos del MODEL, tal com els porta el seu detall. El `fit` va en MAJÚSCULES perquè
  // `Model.fit_type` és un choice ('Regular') i els jocs el declaren pel codi del vocabulari
  // ('REGULAR'): sense normalitzar, un joc que declara el fit no casaria mai amb cap model.
  //
  // I són els del MODEL també quan s'edita una peça, pel mateix motiu que a `EditorTalles`: el
  // contracte nega que els eixos baixin a la prenda, o sigui que no n'hi ha de propis.
  const eixos = {
    target: model.target || null,
    construction: model.construction || null,
    fit: model.fit_type ? String(model.fit_type).toUpperCase() : null,
    garmentGroup: model.garment_type_grup || null,
    garmentTypeId: model.garment_type ?? null,
    garmentTypeItemId: model.garment_type_item ?? null,
  }

  const desar = async () => {
    setDesant(true)
    await onDesar(sel)
    setDesant(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <span style={retolCamp}>{t('dependency.ruleset')}</span>
        {/* EL SELECTOR ÉS EL MATEIX COMPONENT que el pas 4 del wizard (`RuleSetPicker`), pel
            mateix motiu que el pas 2 comparteix `CascadeFinder`: duplicar-lo seria estrenar
            una segona manera de triar una graduació. */}
        <RuleSetPicker
          ruleSets={jocs}
          garmentGroupCodiById={ggCodiById}
          axes={eixos}
          eliminatiu
          selectedId={sel}
          actionLabel={t('model_sheet.use_ruleset')}
          onPick={(rs) => setSel(rs.id)}
        />
      </div>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center', paddingTop: 4 }}>
        {!sel && <span style={{ ...buitText, fontSize: 'var(--fs-caption)' }}>{t('resum_wizard.need_ruleset')}</span>}
        {extra}
        <Boto variant="ter" onClick={onCancel}>{t('model_wizard.cancel')}</Boto>
        {/* EL SEU DESAR ÉS L'ÚNIC BLAU d'aquesta columna (§8f). Re-desar el joc que ja hi és no
            és una acció: el backend no en faria res (`canvia_joc` mira que el joc sigui UN
            ALTRE) i el botó no ha de prometre una feina que no passarà. */}
        <Boto variant="pri" onClick={desar} disabled={desant || !sel || sel === inicialId}>
          {desant ? t('model_wizard.saving') : t('resum_wizard.save_grading')}
        </Boto>
      </div>
    </div>
  )
}

function PasGraduacio({ model, estat, onObrir, desa, onCancel }) {
  const { t } = useTranslation()
  const obert = estat === 'ara'
  const grsId = model?.grading_rule_set ?? null
  const [joc, setJoc] = useState(null)
  const { executa, dialeg } = useConfirmacioRuleset()

  // El joc VIGENT, per poder-lo pintar amb el pas tancat (les eleccions fixades i visibles de §8f).
  useEffect(() => {
    if (!grsId) { setJoc(null); return undefined }
    let viu = true
    gradingRuleSets.get(grsId).then(r => { if (viu) setJoc(r.data || null) }).catch(() => {})
    return () => { viu = false }
  }, [grsId])

  if (!obert) {
    return (
      <FilaDefinicio etiqueta={t('resum_wizard.step_grading')}
        accio={estat === 'blocat' ? null : (
          // El pas ACTUAL ja s'obre sol (i llavors el blau és el seu «Desar graduació»); aquí
          // només s'hi arriba amb el pas FET o amb un altre subespai obert, i en tots dos casos
          // l'acció és secundària: el blau és d'un pas de sol (§8f).
          <BotoCanviar onClick={onObrir}>
            {grsId ? t('resum_wizard.change') : t('model_sheet.define_grading')}
          </BotoCanviar>
        )}>
        {/* BLOQUEJAT amb el MOTIU escrit (§6): un pas apagat i mut no és un estat, és una
            avaria. Abans el portava el `Subespai`; a la fila compacta hi va aquí. */}
        {estat === 'blocat' && (
          <span style={{ ...buitText, fontSize: 'var(--fs-caption)' }}>{t('resum_wizard.needs_sizes')}</span>
        )}
        {estat !== 'blocat' && grsId && (
          // «GRADING BROWNIE 2026 · 142 regles» i prou.
          //
          // 🚩 ELS CHIPS D'EIXOS DEL JOC (target · construcció · fit) SE'N VAN d'aquí. No és un
          // descuit: el disseny validat dona una sola línia a aquest apartat, i aquells eixos són
          // del JOC —no del model— o sigui que repetien en petit el que la fila PEÇA ja diu en
          // gran, i amb el joc de Brownie (eixos BUITS a posta) no en pintaven cap. Qui necessiti
          // el detall del joc el té al picker en obrir «Canviar», que és on es tria.
          <>
            <b>{joc?.nom || model.grading_rule_set_nom || model.grading_rule_set}</b>
            <span style={{ color: 'var(--text-soft)' }}>
              · {t('model_sheet.grading_rules_label')}: {joc?.regles_count ?? 0}
            </span>
          </>
        )}
      </FilaDefinicio>
    )
  }

  return (
    <Subespai num={4} titol={t('resum_wizard.step_grading')} estat="ara">
      <EditorGraduacio model={model} inicialId={grsId}
        // Les confirmacions (joc d'un altre client · esborrat de residents) les porta el hook
        // compartit, que reintenta amb UN flag per cas. Aquí no se'n reimplementa cap. El gest
        // és de la MARE i el 409 és de tot el model: qui desglossa per prenda és el diàleg,
        // amb el `per_garment` que el payload porta des de R11.
        onDesar={id => desa({ grading_rule_set_id: id }, 'resum_wizard.grading_saved',
          p => executa(flags => models.updateStep2(model.id, { ...p, ...flags }), { garment: '' }))}
        onCancel={onCancel} />
      {dialeg}
    </Subespai>
  )
}
