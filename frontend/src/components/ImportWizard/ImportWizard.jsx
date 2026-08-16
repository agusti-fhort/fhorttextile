import { Fragment, useEffect, useState, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Modal from '../ui/Modal'
import { models, poms } from '../../api/endpoints'
import FileDropCard from '../ui/FileDropCard'
// P1 · la graella parla per FILA (`ordre`), no per POM. La lògica pura viu al costat, en un
// mòdul que el runner de Node pot defensar: `node --test src/components/ImportWizard/`.
import {
  aplicaGrading, columnesBuides, comptaValors, construeixBaseValues, construeixMesures,
  construeixTaula, teValorABase,
} from './taulaMesures'
import { sufixIdentitat } from '../../utils/capaInstancia'
import ColumnatIdentitat from '../instancia/ColumnatIdentitat'
import { capaEfectiva, estatDeLaPeca, filaAmbIdentitat, identitatEfectiva, instanciaEfectiva,
         pecaEfectiva, pecaVisible } from './filaPas2'
import { useDiccionariMesures } from '../../utils/diccionariMesuresFont'

const API = import.meta.env.VITE_API_URL || ''

// base64 unicode-safe (per passar el prefill al Size Map Setup via query param).
const encodePrefill = (obj) => btoa(unescape(encodeURIComponent(JSON.stringify(obj))))

// F6 · agrupa una llista per SECCIÓ consecutiva, en l'ordre del document. No reordena res:
// la secció és una capçalera que s'insereix quan canvia, no un criteri d'ordenació — si el
// document repeteix una secció més avall, hi torna a sortir, que és el que diu el paper.
// Sense cap `seccio` retorna UN sol grup amb `seccio: null` → el render queda idèntic al d'abans.
const agrupaPerSeccio = (items, seccioDe) => {
  const grups = []
  for (const item of items) {
    const s = seccioDe(item) || null
    if (!grups.length || grups[grups.length - 1].seccio !== s) grups.push({ seccio: s, items: [] })
    grups[grups.length - 1].items.push(item)
  }
  return grups
}

// Subcapçalera de grup: el mateix fons que la capçalera de la taula de mesures (:983).
const SUBHEAD = {
  padding: '6px 12px', background: '#f5f0ea', fontWeight: 600,
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
  textTransform: 'uppercase', letterSpacing: '0.04em',
}

const STEPS = [
  { n: 1, labelKey: 'import_wizard.step.sizes' },
  { n: 2, labelKey: 'import_wizard.step.poms' },
  { n: 3, labelKey: 'import_wizard.step.measures' },
  { n: 4, labelKey: 'import_wizard.step.fabric' },
  { n: 5, labelKey: 'import_wizard.step.save' },
]

const GOLD = 'var(--gold, #c79a3a)'
const BORDER = 'var(--border)'

// ───────────────────────────── Stepper header ─────────────────────────────
function Stepper({ step }) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, margin: '0 0 20px' }}>
      {STEPS.map((s, i) => {
        const done = s.n < step
        const active = s.n === step
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : '0 0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 'var(--fs-body)', fontWeight: 600,
                background: active ? GOLD : done ? '#3b6d11' : 'transparent',
                color: active || done ? 'var(--white)' : 'var(--text-muted)',
                border: active || done ? 'none' : `1px solid ${BORDER}`,
              }}>{done ? '✓' : s.n}</div>
              <span style={{
                fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400,
                color: active ? 'var(--text-main)' : 'var(--text-muted)', whiteSpace: 'nowrap',
              }}>{t(s.labelKey)}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ flex: 1, height: 1, background: done ? '#3b6d11' : BORDER, margin: '0 10px' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ───────────────────────────── Picker del catàleg de POMs ─────────────────────────────
// R3 · UN sol picker per als DOS llocs on el pas 2 tria un POM del catàleg: el botó
// «+ Afegir POM del catàleg» del final de la llista i el panell de conflicte de fila. Abans
// el primer era un <select> nu amb el catàleg sencer; ara tots dos cerquen per codi o nom.
function PomCatalegPicker({ modelId, onPick, autoFocus }) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [dades, setDades] = useState(null)   // {results, count, truncat, seccions}
  const [focusat, setFocusat] = useState(!!autoFocus)

  // ⚠️ LA PORTA ERA `/api/v1/poms/` I NOMÉS EN SERVIA LA PRIMERA PÀGINA. Mesurat al tenant
  // `fhort` (15/08): 142 POMs actius, 25 a la pàgina 1 → **117 invisibles**, i el filtre del
  // camp corria sobre aquells 25. I el vocabulari del CLIENT no hi era gens: el codi que la
  // fitxa porta escrit viu a `CustomerPOMAlias.client_code`, no a `POMMaster.codi_client` —que
  // es diu «client» però és el codi de la CASA.
  //
  // El mateix defecte, amb el mateix mecanisme, el va pagar el cercador de la Definició manual
  // (79 POMs invisibles de 143, i un duplicat fabricat: el POM 1047). La solució és la SEVA, no
  // una de nova: `poms/cerca/`, que serveix les DUES poblacions en seccions amb el seu
  // recompte, posa l'exacte al davant i cerca des d'UN sol caràcter (els 22 codis d'una lletra
  // del catàleg v4). Amb `?model=` hi entra el vocabulari del client d'aquest model.
  useEffect(() => {
    const cerca = q.trim()
    // Camp buit AMB EL FOCUS POSAT = catàleg SENCER. La lliçó de la Definició manual: qui obre
    // el desplegable per veure QUÈ hi ha —el cas de qui encara no coneix la nomenclatura del
    // client— es trobava un buit i en deduïa que no hi havia catàleg.
    if (!cerca && !focusat) { setDades(null); return }
    const timer = setTimeout(() => {
      poms.cerca({ q: cerca, page_size: 50, ...(modelId ? { model: modelId } : {}) })
        .then(r => setDades(r.data || null))
        .catch(() => setDades(null))
    }, 300)
    return () => clearTimeout(timer)
  }, [q, modelId, focusat])

  const files = dades?.results || []
  const sec = dades?.seccions || {}
  // Les dues poblacions es pinten AMB EL SEU RÈTOL i el seu recompte: un POM amb àlies hi surt
  // dues vegades i totes dues porten al MATEIX `pom_id`. No es demana a ningú que sàpiga que
  // són la mateixa cosa; se li deixa arribar-hi per qualsevol de les dues portes.
  const grups = [
    ['client', t('import_wizard.resol_sec_client'), sec.client],
    ['casa', t('import_wizard.resol_sec_casa'), sec.casa],
  ].filter(([clau]) => files.some(f => f.seccio === clau))

  return (
    <div>
      <input value={q} autoFocus={autoFocus}
        onFocus={() => setFocusat(true)} onChange={e => setQ(e.target.value)}
        placeholder={t('import_wizard.choose_pom')}
        style={{ width: '100%', maxWidth: 380, padding: '6px 9px', borderRadius: 6,
                 border: `1px solid ${BORDER}`, fontSize: 'var(--fs-body)', fontFamily: 'inherit' }} />
      <div style={{ maxWidth: 380, maxHeight: 210, overflowY: 'auto', marginTop: 6,
                    border: `1px solid ${BORDER}`, borderRadius: 6, background: 'var(--white)' }}>
        {files.length === 0 && (
          <div style={{ padding: '8px 10px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
            {t('import_wizard.resol_cap_resultat')}
          </div>
        )}
        {grups.map(([clau, retol, comptes]) => (
          <Fragment key={clau}>
            <div style={{ padding: '4px 10px', background: 'var(--bg-muted)',
                          fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-muted)',
                          textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {retol}{comptes ? ` · ${comptes.mostrats}/${comptes.count}` : ''}
            </div>
            {files.filter(f => f.seccio === clau).map(c => (
              <button key={`${clau}-${c.id}`} type="button"
                onClick={() => onPick({ id: c.id, codi_client: c.codi_client,
                                        nom_client: c.nom_client })}
                style={{ display: 'block', width: '100%', textAlign: 'left', cursor: 'pointer',
                         padding: '6px 10px', fontSize: 'var(--fs-body)', fontFamily: 'inherit',
                         background: 'transparent', border: 'none',
                         borderTop: `1px solid ${BORDER}` }}>
                {/* A la secció del CLIENT mana el seu codi —és el que la fitxa porta escrit— i
                    el de la casa queda al costat. A la de la casa, el de la casa. */}
                <b>{clau === 'client' && c.client_code ? c.client_code : c.codi_client}</b>
                {' · '}{c.nom_client}
                {clau === 'client' && c.client_code && c.client_code !== c.codi_client && (
                  <span style={{ color: 'var(--text-muted)' }}> → {c.codi_client}</span>
                )}
              </button>
            ))}
          </Fragment>
        ))}
      </div>
      {dades?.truncat && (
        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 4 }}>
          {t('import_wizard.resol_mes_resultats', { n: dades.count - files.length })}
        </div>
      )}
    </div>
  )
}

// ───────────────────── Panell de resolució d'una fila (R3) ─────────────────────
// El 409 del catàleg deixava el tècnic amb una sola sortida: sortir del wizard cap al
// catàleg. Aquí la fila té les TRES sortides a sobre —vincular a un candidat, triar del
// catàleg, o crear-ne un de nou amb codi i nom editables— i la decisió segueix sent seva:
// el backend no en tria cap, només diu qui es disputa el codi.
function ResolPanel({ fila, conflicte, res, modelId, crea, setCrea, onVincula, onCrea, onTanca,
                     dicc, capa, instancia, onCapa, onInstancia }) {
  const { t } = useTranslation()
  const candidats = conflicte?.candidats || []
  // El RÈTOL VIU de la columna dreta: la decisió d'aquesta tramesa si n'hi ha, i si no, el
  // vincle que la fila ja portava (una fila aparellada sola que s'obre només per dir de quina
  // mesura del POM parla). Sense POM no hi ha rètol ni «Fet»: no hi ha res a confirmar.
  const vincle = res
    ? (res.accio === 'vincula'
        ? t('import_wizard.resol_fet_vincula', { codi: res.pom_codi, nom: res.pom_nom })
        : t('import_wizard.resol_fet_crea', { codi: res.codi, nom: res.nom }))
    : (fila.pom_master_id ? `${fila.pom_codi} · ${fila.pom_nom || fila.descripcio || ''}` : null)
  const EYEBROW = { fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
                    letterSpacing: '0.04em', color: 'var(--text-muted)', margin: '10px 0 6px' }
  const BTN = { padding: '5px 12px', borderRadius: 6, border: `1px solid ${GOLD}`, cursor: 'pointer',
                background: 'transparent', color: GOLD, fontSize: 'var(--fs-body)', fontFamily: 'inherit' }
  return (
    <div style={{ padding: '10px 14px 14px', background: 'var(--bg-muted)',
                  borderTop: `1px solid ${BORDER}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>
          {t('import_wizard.resol_title', { codi: fila.codi_fitxa || t('import_wizard.no_description') })}
        </div>
        <button type="button" onClick={onTanca}
          style={{ ...BTN, border: `1px solid ${BORDER}`, color: 'var(--text-muted)' }}>
          {t('app.cancel')}
        </button>
      </div>

      {conflicte?.error && (
        <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 6, fontSize: 'var(--fs-body)',
                      background: 'var(--err-bg)', color: 'var(--err)' }}>
          {t([`import_wizard.resol_err_${conflicte.error}`, 'import_wizard.resol_err_generic'],
             { codi: conflicte.codi || fila.codi_fitxa || '', ordre: (conflicte.ordre_ocupat ?? 0) + 1 })}
        </div>
      )}

      {candidats.length > 0 && (
        <>
          <div style={EYEBROW}>{t('import_wizard.resol_vincula_title')}</div>
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 6, background: 'var(--white)',
                        maxWidth: 520 }}>
            {candidats.map((c, i) => (
              <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
                                       borderTop: i ? `1px solid ${BORDER}` : 'none' }}>
                <div style={{ flex: 1, fontSize: 'var(--fs-body)' }}>
                  <b>{c.codi_client}</b> · {c.nom_client}
                  <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                    {c.origen_import
                      ? t('import_wizard.resol_origen_import', { origen: c.origen_import })
                      : t('import_wizard.resol_origen_manual')}
                    {c.pendent_revisio ? ` · ${t('import_wizard.resol_pendent_revisio')}` : ''}
                    {c.actiu ? '' : ` · ${t('import_wizard.resol_inactiu')}`}
                  </div>
                </div>
                <button type="button" disabled={!c.actiu} onClick={() => onVincula(c)}
                  style={{ ...BTN, opacity: c.actiu ? 1 : 0.45, cursor: c.actiu ? 'pointer' : 'not-allowed' }}>
                  {t('import_wizard.resol_vincula_btn')}
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* P2-quater · DUES COLUMNES: les dues meitats de la decisió es veuen ALHORA. Amb el
          bloc d'instància a sota, el desplegable del cercador obert el deixava fora de vista, i
          triar la instància demanava tancar abans el que s'estava mirant. A l'esquerra QUI és
          (catàleg o codi nou), a la dreta DE QUINA de les seves mesures parla la fila.
          `flexWrap` amb una base de 450px: en una finestra estreta cauen l'una sota l'altra
          soles, que és el comportament que ja tenia. */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
      <div style={{ flex: '1 1 450px', minWidth: 0, maxWidth: 520 }}>
      <div style={EYEBROW}>{t('import_wizard.resol_cataleg_title')}</div>
      <PomCatalegPicker modelId={modelId} autoFocus={candidats.length === 0}
        onPick={pm => onVincula({ id: pm.id, codi_client: pm.codi_client,
                                  nom_client: pm.nom_client, actiu: true })} />

      <div style={EYEBROW}>{t('import_wizard.resol_crea_title')}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'flex-end' }}>
        <label style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
          {t('import_wizard.resol_camp_codi')}
          <input value={crea.codi} onChange={e => setCrea({ ...crea, codi: e.target.value })}
            style={{ display: 'block', width: 110, padding: '6px 9px', borderRadius: 6, marginTop: 3,
                     border: `1px solid ${BORDER}`, fontSize: 'var(--fs-body)', fontFamily: 'inherit' }} />
        </label>
        <label style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', flex: '1 1 240px', maxWidth: 380 }}>
          {t('import_wizard.resol_camp_nom')}
          <input value={crea.nom} onChange={e => setCrea({ ...crea, nom: e.target.value })}
            style={{ display: 'block', width: '100%', padding: '6px 9px', borderRadius: 6, marginTop: 3,
                     border: `1px solid ${BORDER}`, fontSize: 'var(--fs-body)', fontFamily: 'inherit' }} />
        </label>
        <button type="button" onClick={onCrea} disabled={!crea.codi.trim()}
          style={{ ...BTN, background: crea.codi.trim() ? GOLD : 'transparent',
                   color: crea.codi.trim() ? 'var(--white)' : 'var(--text-muted)',
                   border: `1px solid ${crea.codi.trim() ? GOLD : BORDER}`,
                   cursor: crea.codi.trim() ? 'pointer' : 'not-allowed' }}>
          {t('import_wizard.resol_crea_btn')}
        </button>
      </div>
      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 6 }}>
        {t('import_wizard.resol_crea_hint')}
      </div>
      </div>

      {/* LA SEGONA MEITAT, SEMPRE A LA VISTA. Abans només es pintava amb la resolució ja presa,
          i per això apareixia i desapareixia sota el desplegable; ara viu a la seva columna i
          es pot triar abans o després de dir quin POM és — l'ordre el posa qui treballa, no la
          pantalla. El rètol viu i el «Fet» sí que demanen que ja hi HAGI POM: una fila que
          encara no en té no té res a confirmar. */}
      <div style={{ flex: '1 1 320px', minWidth: 0 }}>
        {/* Sense rètol de secció: el bloc ja porta la seva capçalera INSTÀNCIA, i escriure-la
            dues vegades seguides fa dubtar de si són dues coses. */}
        <div style={{ height: 10 }} />
        <ColumnatIdentitat valor={instancia} capa={capa} dicc={dicc}
          onTria={onInstancia} onCapa={onCapa} />
        {vincle && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--ok)', marginBottom: 8 }}>
              {vincle}<b>{sufixIdentitat({ capa, instancia }, dicc)}</b>
            </div>
            <button type="button" onClick={onTanca}
              style={{ ...BTN, background: GOLD, color: 'var(--white)' }}>
              {t('import_wizard.resol_fet_btn')}
            </button>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}

export default function ImportWizard({ model, garment = '', garmentNom = '', onCancel, onComplete }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  // P3 · LA IDENTITAT DE LA FILA, VISIBLE. `sufixIdentitat` és la porta única de la casa i
  // torna '' per a la mesura única d'exterior: avui, doncs, la pantalla no canvia ni un píxel.
  // Parla el dia que una fila porta germana — que és el dia que dues files diuen el mateix nom
  // amb xifres diferents, el pitjor que pot ensenyar una taula de mesures.
  const dicc = useDiccionariMesures()
  const lang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  const token = localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const [step, setStep] = useState(1)
  const [sessionToken, setSessionToken] = useState(null)
  const [error, setError] = useState('')
  // LLEI BEACH — resum no-bloquejant del pas 5: columnes del document fora del sistema de talles
  // que s'han descartat (l'import ha escrit les conegudes; s'ha creat un watchpoint al model).
  const [descartades, setDescartades] = useState(null)   // { etiquetes:[], system, model_id }
  const [confirmSizeMap, setConfirmSizeMap] = useState(false)   // 1C-3b: avís abans de saltar a la Library
  const [sizeMapPrefill, setSizeMapPrefill] = useState(null)   // ve de la resposta talles/ (estat PENDENT)

  // Pas 1 — upload + cribratge + reconciliació de talles
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [cribratge, setCribratge] = useState(null)
  const [tallesSel, setTallesSel] = useState([])      // columnes del document mantingudes (labels doc)
  const [systemLabels, setSystemLabels] = useState([]) // etiquetes REALS del model (SizeDefinition)
  const [mapping, setMapping] = useState({})          // aparellament {label_document: label_model}
  const [baseLabel, setBaseLabel] = useState(model.base_size_label || '')  // B5 · talla base (model)
  const [baseAvisos, setBaseAvisos] = useState([])    // B5 · divergències no bloquejants
  const [savingTalles, setSavingTalles] = useState(false)

  // Pas 2 — extracció POMs + matching
  const [extracting, setExtracting] = useState(false)
  const [pomsExtrets, setPomsExtrets] = useState(null)
  const [extraccioMeta, setExtraccioMeta] = useState(null)
  const [savingPoms, setSavingPoms] = useState(false)
  const [showAddPom, setShowAddPom] = useState(false)
  // 409 `codi_duplicat`: el catàleg té 2+ POMs tenant-only amb el mateix codi i el backend no
  // pot triar. NO és un error del wizard (la sessió és intacta i re-desable): és una feina de
  // catàleg pendent, i es mostra com a avís amb els codis, no com el 500 genèric d'abans.
  // R3 · deixa de ser un atzucac: el comptador de dalt resumeix, i la feina es fa a la fila.
  // R3 · l'estat de conflicte VIU A LA FILA: {ordre: {candidats, error, codi, ordre_ocupat}}.
  const [conflictes, setConflictes] = useState({})
  // R3 · decisions preses i encara no enviades: {ordre: {accio:'vincula'|'crea', ...}}.
  const [resolucions, setResolucions] = useState({})
  // P2 · la IDENTITAT triada per fila (`{ordre: {capa, instancia}}`). Viu a part de
  // `resolucions` perquè és una decisió d'un altre gènere —no diu QUIN POM és, sinó DE QUINA de
  // les seves mesures parla la fila— i perquè una fila ja aparellada l'ha de poder triar sense
  // re-vincular res. Al desar es fonen: el backend rep UNA resolució per fila, sencera.
  // P2-quinquies · UN sol mapa per als DOS eixos: dos mapes paral·lels sobre la mateixa fila
  // són dues veritats que un dia discrepen, que és el defecte que aquest tram persegueix.
  const [identitats, setIdentitats] = useState({})
  // SET-2/T8-ter — les peces del model, per al desplegable de la columna. Es demanen un cop i
  // MAI bloquegen: sense elles la columna no es pinta i el pas 2 es comporta com abans (la
  // mateixa llei que el diccionari d'identitat). La mare hi entra sempre com a primera opció:
  // `peces_del_model` la publica com a fila sintètica (`es_mare`), que és exactament per a
  // això —recórrer totes les prendes d'un model amb un sol bucle.
  const [peces, setPeces] = useState([])
  useEffect(() => {
    if (!model?.id) return
    let viu = true
    models.peces(model.id)
      .then(r => { if (viu) setPeces(r.data?.peces || r.data || []) })
      .catch(() => { if (viu) setPeces([]) })
    return () => { viu = false }
  }, [model?.id])

  const [panellOrdre, setPanellOrdre] = useState(null)   // fila amb el panell obert (una alhora)
  const [crea, setCrea] = useState({ codi: '', nom: '' })
  const filaRefs = useRef({})

  // Pas 3 — taula de mesures
  const [taula, setTaula] = useState({})              // {ordre: {talla: valor}} — P1: per FILA
  const [valorsMode, setValorsMode] = useState('absoluts')   // 1C-2b: mode dels valors de la fitxa
  const [gradingLoading, setGradingLoading] = useState(false)
  const [savingMesures, setSavingMesures] = useState(false)

  // Pas 4 — teixit
  const [teixit, setTeixit] = useState({
    fabric_main: '', fabric_composition: '', shrinkage_type: 'NONE',
    shrinkage_warp: '', shrinkage_weft: '', shrinkage_pct: '', shrinkage_iso_key: '', fabric_notes: '',
  })
  const [isoTable, setIsoTable] = useState([])
  const [biaxial, setBiaxial] = useState(true)
  const [savingTeixit, setSavingTeixit] = useState(false)

  // Pas 5 — guardar
  const [confirming, setConfirming] = useState(false)
  // Llei del contenidor: 409 'grading_conflict' (per-regla) i 409 'container_absent' (crear?).
  const [gradingConflict, setGradingConflict] = useState(null)   // {divergencies:[{pom_id,pom,detall}], options}
  const [containerConflict, setContainerConflict] = useState(null) // {customer_nom, garment_type_item, size_system, fit}
  const [conflictChoices, setConflictChoices] = useState({})     // {pom_id: keep_catalog|update_catalog|model_resident}
  // B1 (PRINCIPI DEL SOROLL): 409 'poms_no_mencionats' — mesures vives que el document no porta.
  const [sorollConflict, setSorollConflict] = useState(null)     // {poms:[{pom_id,codi,nom,base_value_cm,origen}], n}
  // B2 (precedència mínima d'orígens): 409 'manual_trepitjat' — el document porta valor per a
  // files que algú va escriure a mà. No es decideix per ell en cap direcció.
  const [manualConflict, setManualConflict] = useState(null)     // {poms:[{pom_id,codi,nom,valor_manual,valor_document}], n}
  // Les decisions del tècnic s'ACUMULEN: resoldre el soroll pot destapar el 409 del contenidor,
  // i el re-POST ha de tornar a portar la tria anterior o el mateix gat es tornaria a disparar.
  const decisionsRef = useRef({})

  // Columnes del document sense parella model → avís (no bloqueja, tret de la base).
  const senseParella = useMemo(() => tallesSel.filter(d => !mapping[d]), [tallesSel, mapping])
  // 1↔1: talles del model aparellades més d'un cop.
  const modelDup = useMemo(() => {
    const seen = {}, dup = new Set()
    tallesSel.forEach(d => { const m = mapping[d]; if (m) { if (seen[m]) dup.add(m); seen[m] = true } })
    return dup
  }, [tallesSel, mapping])
  // B5 · talla base: columna del document aparellada a la talla base del model.
  const baseDocLabel = useMemo(
    () => tallesSel.find(d => mapping[d] === baseLabel) || null,
    [tallesSel, mapping, baseLabel],
  )
  const basePaired = !!baseDocLabel

  // ── Upload → cribratge
  const handleUpload = async () => {
    if (!file) return
    setUploading(true); setError('')
    const fd = new FormData()
    fd.append('document', file)
    fd.append('model_id', model.id)
    fd.append('garment_type_item_code', model.garment_type_item_code || '')
    // SET-2/T8 — LA PRENDA DE DESTÍ, i aquesta és l'ÚNICA porta per on entra al pipeline:
    // a partir d'aquí el backend la llegeix de la sessió i cap altre pas la torna a enviar.
    // `''` és la mare, que és el camí de sempre.
    fd.append('garment', garment || '')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/cribratge/`, {
        method: 'POST', headers: authHeaders, body: fd,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setUploading(false); return }
      setSessionToken(data.token)
      setCribratge(data)
      const docs = data.run_talles_document || []
      setTallesSel(docs)
      await loadProposal(data.token, docs)
    } catch (e) {
      setError(t('import_wizard.err_connection', { detail: String(e) }))
    }
    setUploading(false)
  }

  const removeTalla = (label) => {
    setTallesSel(tallesSel.filter(tt => tt !== label))
    setMapping(prev => { const n = { ...prev }; delete n[label]; return n })
  }
  const setPair = (docLabel, modelLabel) =>
    setMapping(prev => ({ ...prev, [docLabel]: modelLabel }))

  // Carrega l'auto-proposta d'aparellament + etiquetes REALS del model (pas 1).
  const loadProposal = async (token, docs) => {
    const res = await fetch(`${API}/api/v1/import-sessions/${token}/talles/`, {
      method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ talles_seleccionades: docs }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); return }
    setSystemLabels(data.system_labels || [])
    const mp = {}
    for (const p of (data.talla_mapping || [])) mp[p.document] = p.model
    setMapping(mp)
    setBaseLabel(data.base_size_label || '')
    setBaseAvisos(data.base_avisos || [])
    setSizeMapPrefill(data.size_map_prefill || null)
  }

  // Desa mapping (+ opcionalment la talla base) i retorna la resposta validada.
  const patchTalles = async (extra = {}) => {
    const talla_mapping = tallesSel.map(d => ({ document: d, model: mapping[d] || '' }))
    const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/talles/`, {
      method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ talles_seleccionades: tallesSel, talla_mapping, ...extra }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); return null }
    if (data.base_size_label !== undefined) setBaseLabel(data.base_size_label || '')
    setBaseAvisos(data.base_avisos || [])
    setSizeMapPrefill(data.size_map_prefill || null)
    return data
  }

  // B5 · canvia la talla base del model (persisteix a base_size_label via /talles/).
  const changeBase = async (modelLabel) => {
    setSavingTalles(true); setError('')
    await patchTalles({ base_size_label: modelLabel })
    setSavingTalles(false)
  }

  // Obre el Size Map Setup pre-omplert. Usa el prefill del backend si el tenim;
  // si no, el construeix a partir del que ja sabem (model + talles seleccionades).
  const goConfigureRun = () => {
    const prefill = sizeMapPrefill || {
      target_codi: model?.target || null,
      labels: tallesSel,
      base_size: model?.base_size_label || null,
      import_session_token: sessionToken,
      model_id: model?.id ?? null,
    }
    // 1C-3b: salta a la Size Library (drawer auto-obert per ?prefill). Decisió (ii):
    // sense represa automàtica — l'usuari es queda a la Library i torna al model manualment.
    // token/model_id es deixen al prefill (inerts al camí Library).
    navigate(`/size-library?prefill=${encodeURIComponent(encodePrefill(prefill))}`)
  }

  const handleContinue = async () => {
    setSavingTalles(true); setError('')
    const data = await patchTalles()
    setSavingTalles(false)
    if (!data) return
    if ((data.errors || []).length) { setError(data.errors.join(' ')); return }
    if (data.ready) { setStep(2); runExtraccio() }
    else setError(t('import_wizard.sizes_unpaired', { sizes: (data.no_aparellades || []).join(', ') }))
  }

  // Bloqueig del pas 1: cada columna doc aparellada, 1↔1, i la talla base aparellada (B5).
  const canContinue = tallesSel.length > 0 && senseParella.length === 0
    && modelDup.size === 0 && basePaired && !savingTalles

  // ── Pas 2 — extracció completa (Crida 2)
  const runExtraccio = async () => {
    setExtracting(true); setError('')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/extraccio/`, {
        method: 'POST', headers: authHeaders,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setExtracting(false); return }
      setPomsExtrets(data.poms_extrets || [])
      setExtraccioMeta({ header: data.header, base_size: data.base_size, sizes: data.sizes,
                         grading_status: data.grading_status, avisos: data.avisos || [],
                         // F5 · informe del llibre: quines pestanyes hi ha i quina s'ha llegit.
                         fulls: data.fulls || [], full: data.full || null,
                         // SET-2/T8-ter · la proposta secció→peça i, sobretot, les seccions
                         // que no en tenen: el pas 2 les ha de poder DIR.
                         proposta_peces: data.proposta_peces || null })
      if (data.suggested_valors_mode === 'absoluts' || data.suggested_valors_mode === 'deltes')
        setValorsMode(data.suggested_valors_mode)
    } catch (e) {
      setError(t('import_wizard.err_connection', { detail: String(e) }))
    }
    setExtracting(false)
  }

  // F5 · el tècnic tria quin full del llibre s'importa. Es desa amb el MATEIX PATCH de talles
  // (que reenvia el mapping sencer, així que no s'hi perd res) i es torna a extreure: el full
  // és una entrada del parser, no un filtre de la sortida.
  const canviaFull = async (nom) => {
    if (!nom || nom === extraccioMeta?.full) return
    setExtracting(true); setError('')
    const data = await patchTalles({ full_seleccionat: nom })
    if (!data) { setExtracting(false); return }
    await runExtraccio()
  }

  const fulls = extraccioMeta?.fulls || []
  const fullsAmbPoms = fulls.filter(f => f.passa_porta)
  // Fulls amb files de POM que NO s'han pogut llegir: hi ha contingut i s'està perdent.
  const fullsNoLlegits = fulls.filter(f => !f.passa_porta && f.n_files_amb_codi > 0)
  const potTriarFull = fullsAmbPoms.length > 1 || fullsNoLlegits.length > 0

  const togglePom = (idx) => setPomsExtrets(pomsExtrets.map((p, i) =>
    i === idx ? { ...p, actiu: !p.actiu } : p))

  // R3 · el marcatge «tenant-only» a cegues (crear amb el codi del document sense mirar-lo)
  // ha mort: activar una fila sense match és decidir QUÈ és, i això es fa al panell de la
  // fila (resolució 'crea' amb codi i nom editables). El contracte `poms_tenant_only` del
  // backend segueix viu i cobert per tests; el que ja no hi ha és la via cega des d'aquí.

  // El catàleg ja NO es precarrega: cada picker el demana al cercador del servidor
  // (`poms/cerca/`), que és qui sap servir les dues poblacions. La còpia local que hi havia
  // aquí era la que només en tenia 25 de 142.

  // ── R3 · el conflicte es resol a la fila ──────────────────────────────────────
  const obrePanell = (p) => {
    const res = resolucions[p.ordre]
    setCrea({
      codi: (res?.accio === 'crea' ? res.codi : '') || p.codi_fitxa || '',
      nom: (res?.accio === 'crea' ? res.nom : '') || p.descripcio || p.pom_nom || '',
    })
    setPanellOrdre(p.ordre)
  }

  // P2-ter/2 · `tanca` és de qui la crida. Des del panell, triar el POM ja NO el tanca: la
  // decisió té dues meitats —quin POM és i de quina de les seves mesures parla la fila— i
  // tancar a la primera obligava a reobrir per a la segona. El tanca «Fet».
  const posaResolucio = (ordre, res, { tanca = true } = {}) => {
    setResolucions(prev => ({ ...prev, [ordre]: res }))
    setConflictes(prev => { const n = { ...prev }; delete n[ordre]; return n })
    setPomsExtrets(prev => prev.map(p =>
      p.ordre === ordre ? { ...p, actiu: true, tenant_only: false } : p))
    if (tanca) setPanellOrdre(null)
  }

  const treuResolucio = (ordre) => {
    setResolucions(prev => { const n = { ...prev }; delete n[ordre]; return n })
    setPomsExtrets(prev => prev.map(p => p.ordre === ordre ? { ...p, actiu: false } : p))
  }

  // Marca les files afectades i porta el tècnic a la primera. El wizard no es queda mai
  // amb un missatge global i cap acció possible.
  const marcaConflictes = (nous) => {
    setConflictes(nous)
    const primer = Object.keys(nous).map(Number).sort((a, b) => a - b)[0]
    if (primer === undefined) return
    const fila = (pomsExtrets || []).find(p => p.ordre === primer)
    if (fila) obrePanell(fila)
    setTimeout(() => filaRefs.current[primer]?.scrollIntoView(
      { behavior: 'smooth', block: 'center' }), 60)
  }

  const addPomManual = (pm) => {
    if (pomsExtrets.some(p => p.pom_master_id === pm.id)) { setShowAddPom(false); return }
    setPomsExtrets([...pomsExtrets, {
      codi_fitxa: '', descripcio: pm.nom_client || '', pom_master_id: pm.id,
      pom_codi: pm.codi_client, pom_nom: pm.nom_client, match_type: 'manual',
      confidence: 'HIGH', values: {}, actiu: true, ordre: pomsExtrets.length,
    }])
    setShowAddPom(false)
  }

  const handleContinuePoms = async () => {
    setSavingPoms(true); setError('')
    const actius = pomsExtrets.filter(p => p.actiu)
    // Les resolucions manen: la fila que en porta una no viatja pels camins a cegues
    // (`poms_confirmats` amb el vincle vell, `poms_tenant_only` amb el codi del document).
    //
    // P2 · LA INSTÀNCIA VIATJA PER AQUÍ, i no per un camp nou: dir «aquesta fila és el POM B a
    // baix» és UNA decisió, no dues, i el backend ja la sap llegir sencera (`_pla_de_resolucions`).
    // Una fila que només tria instància n'estrena una de `vincula` al POM que ja tenia.
    const llistaRes = actius
      .filter(p => resolucions[p.ordre] || (identitats[p.ordre] && p.pom_master_id))
      .map(p => {
        const base = resolucions[p.ordre]
          || { accio: 'vincula', pom_master_id: p.pom_master_id,
               pom_codi: p.pom_codi, pom_nom: p.pom_nom }
        // Els DOS eixos hi entren només si s'han triat: una tramesa que no en parli deixa la
        // fila com estava, i el backend hi posa els literals de sempre (exterior · única).
        return { ordre: p.ordre, ...base, ...(identitats[p.ordre] || {}) }
      })
    const ambRes = new Set(llistaRes.map(r => r.ordre))
    const ids = actius.filter(p => p.pom_master_id && !ambRes.has(p.ordre)).map(p => p.pom_master_id)
    const tenantOnly = actius
      .filter(p => !p.pom_master_id && p.tenant_only && !ambRes.has(p.ordre))
      .map(p => p.ordre)
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/poms/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        // P2 · `files_confirmades` diu QUINES FILES entren, per `ordre`. `poms_confirmats` es
        // queda perquè té una altra feina: incorporar POMs del catàleg que el document no
        // menciona, i aquells encara no tenen fila amb què demanar-se.
        body: JSON.stringify({ poms_confirmats: ids, poms_tenant_only: tenantOnly,
                               resolucions: llistaRes,
                               files_confirmades: actius.map(p => p.ordre),
                               // SET-2/T8-ter · DE QUI ÉS CADA FILA. Només les DECIDIDES: una
                               // proposta que ningú ha confirmat no és una decisió i no pot
                               // viatjar com si ho fos (`estatDeLaPeca`, provat a part).
                               files_garment: pomsExtrets
                                 .filter(p => estatDeLaPeca(p, identitats) === 'decidit')
                                 .map(p => ({ ordre: p.ordre,
                                              garment: pecaEfectiva(p, identitats, garment || '') })) }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.status === 409 && data.error === 'codi_duplicat') {
        // El codi del document té 2+ POMs al catàleg: marca les files que el porten i obre
        // la primera. El comptador de dalt només resumeix.
        const codis = data.codis || []
        const cands = data.candidats || {}
        const nous = {}
        for (const p of pomsExtrets) {
          const codi = (p.codi_fitxa || '').trim()
          if (!p.pom_master_id && codis.includes(codi)) {
            nous[p.ordre] = { candidats: cands[codi] || [], error: 'codi_duplicat', codi }
          }
        }
        marcaConflictes(nous); setSavingPoms(false); return
      }
      if (res.status === 409 && data.error === 'resolucions_invalides') {
        // Error PER FILA. Les resolucions bones es conserven (es reenviaran); només es
        // desfan les que han fallat, perquè el tècnic les torni a decidir.
        const errors = data.errors || []
        const nous = {}
        for (const e of errors) {
          nous[e.ordre] = { candidats: e.candidats || [], error: e.error, codi: e.codi,
                            ordre_ocupat: e.ordre_ocupat }
        }
        setResolucions(prev => {
          const n = { ...prev }
          for (const e of errors) delete n[e.ordre]
          return n
        })
        marcaConflictes(nous); setSavingPoms(false); return
      }
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingPoms(false); return }
      // El backend retorna els POMs amb els pom_master_id (tenant-only i resolucions) ja
      // assignats: les decisions pendents ja són dades i l'estat local de resolució mor aquí.
      const updated = data.poms_extrets || pomsExtrets
      setPomsExtrets(updated)
      // …i la instància també: ha pujat a la fila (`capa`/`instancia` de `poms_extrets`) i
      // llegir-la de dos llocs alhora és com neixen les discrepàncies que ningú no veu.
      setResolucions({}); setConflictes({}); setPanellOrdre(null); setIdentitats({})
      buildTaula(updated)
      setStep(3)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingPoms(false)
  }

  const pomsActius = (pomsExtrets || []).filter(p => p.actiu).length

  // F6 · grups de secció del pas 2. Es porta l'índex ORIGINAL a dins: els toggles hi indexen.
  const grupsPoms = agrupaPerSeccio(
    (pomsExtrets || []).map((p, idx) => ({ p, idx })), x => x.p.seccio)
  // Els POMs afegits a mà del catàleg no vénen de cap secció del document. Quan la fitxa SÍ
  // que en té, se'ls posa una capçalera pròpia: sense ella semblaria que pengen de l'última.
  const pomsAmbSeccions = grupsPoms.some(g => g.seccio)

  // ── Pas 3 — taula de mesures
  const pomsTaula = (pomsExtrets || []).filter(p => p.actiu)  // files = POMs actius
  const grupsTaula = agrupaPerSeccio(pomsTaula, p => p.seccio)     // F6
  const taulaAmbSeccions = grupsTaula.some(g => g.seccio)
  // La columna base de la taula de mesures és la label DOCUMENT aparellada amb la talla base
  // del model (B5); si no, fallback a l'heurística anterior.
  const baseSize = baseDocLabel
    || ((extraccioMeta?.base_size && tallesSel.includes(extraccioMeta.base_size))
      ? extraccioMeta.base_size : tallesSel[0])

  const buildTaula = (src) => setTaula(construeixTaula(src || pomsExtrets, tallesSel))

  const setCell = (clau, talla, val) =>
    setTaula(prev => ({ ...prev, [clau]: { ...(prev[clau] || {}), [talla]: val } }))

  // Columnes (talles) completament buides → ofereix generar grading.
  const emptyCols = columnesBuides(pomsTaula, tallesSel, taula)
  const baseTeValors = teValorABase(pomsTaula, taula, baseSize)

  const handleGenerarGrading = async () => {
    setGradingLoading(true); setError('')
    const base_values = construeixBaseValues(pomsTaula, taula, baseSize)
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/grading-preview/`, {
        method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_values }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setGradingLoading(false); return }
      // Omple NOMÉS les cel·les buides; preserva els valors extrets del document. La resposta
      // arriba amb la mateixa clau amb què s'ha preguntat i el backend ho declara a `clau`.
      setTaula(prev => aplicaGrading(prev, pomsTaula, tallesSel, data.grading || {}, data.clau))
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setGradingLoading(false)
  }

  const handleContinueMesures = async () => {
    setSavingMesures(true); setError('')
    const mesures = construeixMesures(pomsTaula, tallesSel, taula)
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/mesures/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mesures, valors_mode: valorsMode }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingMesures(false); return }
      loadIso()
      setStep(4)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingMesures(false)
  }

  // 1C-3 — destí Size Library: desa mesures (+valors_mode) i salta al drawer de la Library amb
  // el prefill ENRIQUIT (run+base+target+POMs en absoluts). Reutilitza el camí provat
  // size_map_create_view; aquí només preparem el prefill i naveguem.
  const goCrearLibrary = async () => {
    setSavingMesures(true); setError('')
    const mesures = construeixMesures(pomsTaula, tallesSel, taula)
    try {
      await fetch(`${API}/api/v1/import-sessions/${sessionToken}/mesures/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mesures, valors_mode: valorsMode }),
      })
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/library-prefill/`, {
        method: 'POST', headers: authHeaders,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingMesures(false); return }
      navigate(`/size-library?prefill=${encodeURIComponent(encodePrefill(data))}`)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingMesures(false)
  }

  // ── Pas 4 — teixit
  const loadIso = async () => {
    if (isoTable.length) return
    try {
      const res = await fetch(`${API}/api/v1/models/iso-shrinkage/`, { headers: authHeaders })
      const data = await res.json().catch(() => [])
      setIsoTable(Array.isArray(data) ? data : [])
    } catch { /* iso opcional */ }
  }

  const selectIso = (entry) => {
    setTeixit(t => ({ ...t, shrinkage_type: 'ISO', shrinkage_iso_key: entry.id,
                      shrinkage_warp: entry.warp, shrinkage_weft: entry.weft, shrinkage_pct: '' }))
    setBiaxial(true)
  }

  const buildTeixitPayload = () => {
    const p = {
      fabric_main: teixit.fabric_main, fabric_composition: teixit.fabric_composition,
      shrinkage_type: teixit.shrinkage_type, fabric_notes: teixit.fabric_notes,
      shrinkage_iso_key: teixit.shrinkage_type === 'ISO' ? teixit.shrinkage_iso_key : '',
    }
    if (biaxial) {
      p.shrinkage_warp = teixit.shrinkage_warp !== '' ? parseFloat(teixit.shrinkage_warp) : null
      p.shrinkage_weft = teixit.shrinkage_weft !== '' ? parseFloat(teixit.shrinkage_weft) : null
      p.shrinkage_pct = null
    } else {
      p.shrinkage_pct = teixit.shrinkage_pct !== '' ? parseFloat(teixit.shrinkage_pct) : null
      p.shrinkage_warp = null; p.shrinkage_weft = null
    }
    return p
  }

  const handleSaveTeixit = async (skip) => {
    setSavingTeixit(true); setError('')
    try {
      if (!skip) {
        const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/teixit/`, {
          method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
          body: JSON.stringify(buildTeixitPayload()),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingTeixit(false); return }
      }
      setStep(5)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingTeixit(false)
  }

  // ── Pas 5 — confirmar
  const nValors = comptaValors(pomsTaula, tallesSel, taula)
  const teixitInformat = !!(teixit.fabric_main || teixit.fabric_composition ||
    teixit.shrinkage_iso_key || teixit.shrinkage_warp || teixit.shrinkage_pct)

  // Llei del contenidor — avís-i-confirma conscient. El backend torna 409:
  //  · 'container_absent' → el client no té contenidor per la combinació: crear? (container_choice)
  //  · 'grading_conflict' → regles de la fitxa que contradiuen el catàleg: tria per-POM
  //    (conflict_resolutions {pom_id: keep_catalog|update_catalog|model_resident}).
  // `bodyExtra` és el que afegim al POST en re-confirmar amb la decisió del tècnic.
  const handleConfirmar = async (bodyExtra = {}) => {
    setConfirming(true); setError('')
    const body = { ...decisionsRef.current, ...bodyExtra }
    decisionsRef.current = body
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/confirmar/`, {
        method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (res.status === 409 && data.conflict) {
        if (data.tipus === 'poms_no_mencionats') {
          setSorollConflict(data); setManualConflict(null); setContainerConflict(null); setGradingConflict(null)
        }
        else if (data.tipus === 'manual_trepitjat') {
          setManualConflict(data); setSorollConflict(null); setContainerConflict(null); setGradingConflict(null)
        }
        else if (data.tipus === 'container_absent') { setContainerConflict(data); setGradingConflict(null) }
        else if (data.tipus === 'grading_conflict') {
          setGradingConflict(data); setContainerConflict(null)
          // per defecte: mantenir el catàleg per a cada POM en conflicte.
          const defaults = {}
          for (const d of (data.divergencies || [])) defaults[d.pom_id] = 'keep_catalog'
          setConflictChoices(defaults)
        }
        setConfirming(false); return
      }
      if (res.status === 422 && data.tipus === 'base_size_absent') {
        setError(t('import_wizard.err_base_size_absent', {
          base_size: data.base_size, etiquetes: (data.etiquetes || []).join(', ') || '—' }))
        setConfirming(false); return
      }
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setConfirming(false); return }
      setGradingConflict(null); setContainerConflict(null); setSorollConflict(null); setManualConflict(null)
      decisionsRef.current = {}
      // LLEI BEACH: si el backend ha descartat columnes fora del sistema, NO tanquem en silenci —
      // ho mostrem com a avís (no error) i deixem que el tècnic ho confirmi abans de tancar.
      if ((data.columnes_descartades || []).length) {
        setDescartades({ etiquetes: data.columnes_descartades,
                         system: data.size_system_codi || '', model_id: data.model_id })
        setConfirming(false); return
      }
      onComplete && onComplete(data.model_id)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setConfirming(false)
  }

  // ─────────────────────────── Render ───────────────────────────
  return (
    <div style={{ }}>
      <Stepper step={step} />

      {/* SET-2/T8 · LA PRENDA DE DESTÍ, DITA COM UN FET.
          **El wizard no pregunta mai de quina peça és l'import**: la peça la fixa el context
          (el contenidor des d'on s'ha premut «Importar taula») i aquí només es MOSTRA, perquè
          qui està important sàpiga on aterra la feina sense haver-ho d'anar a comprovar.
          Només surt quan hi HA prenda: a un model d'una sola peça —el 100% del corpus d'avui—
          seria soroll dir «important a la peça principal» quan no n'hi ha cap altra. */}
      {!!garment && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
                      padding: '6px 12px', borderRadius: 8, background: 'var(--bg-main)',
                      border: `0.5px solid ${BORDER}`, fontSize: 'var(--fs-body)' }}>
          <i className="ti ti-shirt" aria-hidden="true" style={{ fontSize: 15, color: GOLD }} />
          <span style={{ color: 'var(--text-muted)' }}>{t('import_wizard.desti_peca')}</span>
          <strong>{garmentNom || garment}</strong>
        </div>
      )}

      {error && (
        <div style={{ background: '#fff0f0', border: '1px solid #f0c0c0', color: '#a32d2d',
                      borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* LLEI BEACH — avís (no error) del resum: columnes descartades per ser fora del sistema. */}
      {descartades && (
        <div style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold)',
                      color: 'var(--text-main)', borderRadius: 8, padding: '10px 14px',
                      fontSize: 'var(--fs-body)', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {t('import_wizard.cols_descartades_title')}
          </div>
          <div style={{ marginBottom: 10 }}>
            {t('import_wizard.cols_descartades_body', {
              n: descartades.etiquetes.length,
              system: descartades.system,
              labels: descartades.etiquetes.join(', '),
            })}
          </div>
          <button type="button"
            onClick={() => { const id = descartades.model_id; setDescartades(null); onComplete && onComplete(id) }}
            style={{ padding: '6px 14px', border: '1px solid var(--gold)', borderRadius: 6,
                     background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
            {t('import_wizard.cols_descartades_done')}
          </button>
        </div>
      )}

      {/* ═══════════════ PAS 1 — TALLES ═══════════════ */}
      {step === 1 && !cribratge && (
        <div>
          <div style={{ marginBottom: 16 }}>
            {/* El backend NO valida extensió en aquesta porta: `import_session_cribratge_view`
                desa el que li arriba, o sigui que aquesta llista és l'ÚNIC filtre del camí i ha
                de dir exactament el que el cribratge sap llegir — `_cribratge_content_block`
                (extraction_views.py:530-563): PDF · xlsx/xls · image/jpeg · image/png ·
                image/webp. El `.webp` hi faltava: és l'únic format que el servidor anomena
                explícitament i que el diàleg de fitxers no deixava triar. */}
            <FileDropCard
              accept={['.xlsx', '.xls', '.pdf', '.png', '.jpg', '.jpeg', '.webp']}
              icon="ti-file-spreadsheet"
              title={t('import_wizard.drop_file')}
              required
              file={file}
              onFile={setFile}
              disabled={uploading}
              hint={t('import_wizard.file_hint')}
            />
          </div>
          {file && (
            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={handleUpload} disabled={uploading}
                style={{ padding: '10px 24px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                         fontWeight: 600, background: uploading ? '#ccc' : GOLD, color: 'var(--white)',
                         cursor: uploading ? 'not-allowed' : 'pointer' }}>
                {uploading ? t('import_wizard.analyzing_doc') : t('import_wizard.analyze_sizes')}
              </button>
            </div>
          )}
        </div>
      )}

      {step === 1 && cribratge && (
        <div>
          {/* Aparellament document ⟷ model (LA LLEI de la sessió) */}
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
            {t('import_wizard.pairing_intro')}
          </div>

          {/* B5 · targeta de la TALLA BASE (selector limitat a les SizeDefinition del system) */}
          <div style={{ border: `1px solid ${basePaired ? '#c0dd97' : '#f0c0c0'}`, borderRadius: 8,
                        padding: '10px 12px', marginBottom: 12, background: basePaired ? '#f7fbf2' : '#fff6f6' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>★ {t('import_wizard.base_size')}:</span>
              <select value={baseLabel} disabled={savingTalles} onChange={e => changeBase(e.target.value)}
                style={{ padding: '4px 8px', borderRadius: 6, border: `1px solid ${BORDER}`, fontSize: 'var(--fs-body)' }}>
                {systemLabels.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <span style={{ color: 'var(--text-muted)' }}>⟷</span>
              <span style={{ fontSize: 'var(--fs-body)', color: basePaired ? '#3b6d11' : '#a32d2d' }}>
                {baseDocLabel || t('import_wizard.base_unpaired')}
              </span>
            </div>
            {baseAvisos.map((a, i) => (
              <div key={i} style={{ marginTop: 6, fontSize: 'var(--fs-small)', color: GOLD }}>⚠ {a}</div>
            ))}
          </div>

          {/* Taula d'aparellament: una fila per etiqueta del document, selector de talla del model */}
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12, marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 10, fontSize: 'var(--fs-body)', fontWeight: 600,
                          color: 'var(--text-muted)', paddingBottom: 6, borderBottom: `0.5px solid ${BORDER}`, marginBottom: 6 }}>
              <div style={{ width: 110 }}>{t('import_wizard.doc_sizes')} <span style={{ fontWeight: 400 }}>({cribratge.sistema_talles})</span></div>
              <div style={{ width: 20 }} />
              <div>{t('import_wizard.model_sizes')}</div>
            </div>
            {tallesSel.map(d => {
              const m = mapping[d] || ''
              const isBaseRow = !!m && m === baseLabel
              const dup = !!m && modelDup.has(m)
              const state = !m ? 'unpaired' : dup ? 'dup' : 'ok'
              return (
                <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' }}>
                  <div style={{ width: 110, fontWeight: isBaseRow ? 700 : 400 }}>
                    {isBaseRow ? '★ ' : ''}{d}
                  </div>
                  <span style={{ width: 20, color: 'var(--text-muted)', textAlign: 'center' }}>⟷</span>
                  <select value={m} disabled={savingTalles} onChange={e => setPair(d, e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: 6, fontSize: 'var(--fs-body)', minWidth: 130,
                             border: `1px solid ${state === 'ok' ? '#c0dd97' : '#f0c0c0'}` }}>
                    <option value="">{t('import_wizard.no_pair')}</option>
                    {systemLabels.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <span title={t(`import_wizard.pair_${state}`)}
                    style={{ color: state === 'ok' ? '#3b6d11' : '#a32d2d' }}>
                    {state === 'ok' ? '✓' : '⚠'}
                  </span>
                  <button type="button" onClick={() => removeTalla(d)} title={t('import_wizard.remove_size')}
                    style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 'var(--fs-h3)' }}>×</button>
                </div>
              )
            })}
          </div>

          {/* Columnes del document sense parella → avís no bloquejant (la base sí bloqueja) */}
          {senseParella.length > 0 && (
            <div style={{ background: '#fff0f0', border: '1px solid #f0c0c0', borderRadius: 8,
                          padding: '10px 12px', marginBottom: 16 }}>
              <div style={{ fontSize: 'var(--fs-body)', color: '#a32d2d', marginBottom: 8 }}>
                {t('import_wizard.unpaired_warn', { count: senseParella.length, sizes: senseParella.join(', ') })}
              </div>
              <button type="button" onClick={() => setConfirmSizeMap(true)}
                style={{ padding: '6px 14px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
                         border: '0.5px solid #c0c0c0', background: 'transparent', color: '#666' }}>
                ⚙ {t('import_wizard.configure_client_run')}
              </button>
            </div>
          )}

          {/* Navegació */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
            <button type="button" onClick={onCancel}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              ← {t('app.cancel')}
            </button>
            <button type="button" onClick={handleContinue} disabled={!canContinue}
              title={canContinue ? '' : t('import_wizard.resolve_mismatch')}
              style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                       fontWeight: 500, color: 'var(--white)', background: canContinue ? GOLD : '#ccc',
                       cursor: canContinue ? 'pointer' : 'not-allowed' }}>
              {t('import_wizard.continue_poms')}
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 2 — POMs ═══════════════ */}
      {step === 2 && (
        <div>
          {/* Talles confirmades (Pas 1) sempre visibles */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 6 }}>
              {t('import_wizard.confirmed_sizes')}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {tallesSel.map(t => (
                <span key={t} style={{ padding: '3px 9px', borderRadius: 6, fontSize: 'var(--fs-body)',
                                       border: `1px solid #c0dd97`, background: '#f0f9f0', color: '#3b6d11' }}>{t}</span>
              ))}
            </div>
          </div>

          {extracting && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>⏳</div>
              <div style={{ fontSize: 'var(--fs-h3)' }}>{t('import_wizard.extracting_poms')}</div>
              <div style={{ fontSize: 'var(--fs-body)', marginTop: 4 }}>{t('import_wizard.vision_analysis')}</div>
            </div>
          )}

          {/* 409 codi_duplicat — R3: ja NO és un atzucac. El conflicte es resol fila a fila
              (panell inline) i això de dalt només compta quantes en queden. */}
          {Object.keys(conflictes).length > 0 && (
            <div style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold)',
                          color: 'var(--text-main)', borderRadius: 8, padding: '10px 14px',
                          fontSize: 'var(--fs-body)', marginBottom: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>
                {t('import_wizard.codi_duplicat_title')}
              </div>
              <div>
                {t('import_wizard.codi_duplicat_body', {
                  n: Object.keys(conflictes).length,
                  codis: Object.keys(conflictes).map(o => {
                    const fila = (pomsExtrets || []).find(p => String(p.ordre) === String(o))
                    return conflictes[o].codi || fila?.codi_fitxa || fila?.pom_codi || ''
                  }).filter(Boolean).join(', '),
                })}
              </div>
            </div>
          )}

          {/* F5 · el llibre té més d'un full. L'avís surt sempre que n'hi hagi més d'un; el
              selector, només si hi ha res a triar de debò (2+ fulls llegibles, o fulls amb
              POMs que no s'han pogut llegir). */}
          {!extracting && fulls.length > 1 && (
            <div style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold)',
                          color: 'var(--text-main)', borderRadius: 8, padding: '10px 14px',
                          fontSize: 'var(--fs-body)', marginBottom: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>
                {t('import_wizard.fulls_title', { n: fullsAmbPoms.length })}
              </div>
              <div style={{ marginBottom: potTriarFull ? 10 : 0 }}>
                {t('import_wizard.fulls_llegit', { full: extraccioMeta?.full || '—' })}
              </div>
              {potTriarFull && (
                <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>{t('import_wizard.fulls_tria')}</span>
                  <select value={extraccioMeta?.full || ''}
                    onChange={e => canviaFull(e.target.value)}
                    style={{ padding: '6px 8px', borderRadius: 6, fontSize: 'var(--fs-body)',
                             border: `1px solid ${BORDER}`, fontFamily: 'inherit', minWidth: 260 }}>
                    {fulls.map(f => (
                      <option key={f.nom} value={f.nom} disabled={!f.passa_porta}>
                        {f.passa_porta
                          ? t('import_wizard.fulls_opcio', { nom: f.nom, n: f.n_files_amb_codi })
                          : t('import_wizard.fulls_opcio_illegible', { nom: f.nom })}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          )}

          {!extracting && pomsExtrets && (
            <div>
              {/* Avisos d'extracció */}
              {(extraccioMeta?.avisos || []).length > 0 && (
                <div style={{ background: '#fdf6ee', border: '1px solid var(--gold-border)', color: 'var(--gold)',
                              borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 12 }}>
                  {extraccioMeta.avisos.map((a, i) => <div key={i}>⚠ {a}</div>)}
                </div>
              )}

              {/* SET-2/T8-ter · LES SECCIONS QUE NO TENEN PEÇA. És una ABSÈNCIA i s'ha de dir:
                  un document amb secció SHORT sobre un model sense peça Short vol dir que en
                  falta una, i el silenci hi deixaria set files aterrant a la mare sense que
                  ningú se n'adonés. No barra: la columna segueix manant. */}
              {(extraccioMeta?.proposta_peces?.seccions_sense_peca || []).length > 0 && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start',
                              background: 'var(--bg-main)', border: `0.5px solid ${BORDER}`,
                              borderRadius: 8, padding: '8px 12px', marginBottom: 12,
                              fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                  <i className="ti ti-info-circle" aria-hidden="true"
                     style={{ fontSize: 15, color: GOLD, flexShrink: 0, marginTop: 1 }} />
                  <span>{t('import_wizard.peces_seccions_sense_peca', {
                    seccions: (extraccioMeta.proposta_peces.seccions_sense_peca).join(' · '),
                  })}</span>
                </div>
              )}

              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
                {t('import_wizard.poms_summary', { count: pomsExtrets.length, active: pomsActius })}
                {extraccioMeta?.base_size && <> · {t('import_wizard.base_size_label')}: <b>{extraccioMeta.base_size}</b></>}
              </div>

              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
                {grupsPoms.map((grup, gi) => (
                  <Fragment key={`g${gi}`}>
                    {(grup.seccio || pomsAmbSeccions) && (
                      <div style={{ ...SUBHEAD, borderTop: gi ? `1px solid ${BORDER}` : 'none' }}>
                        {grup.seccio || t('import_wizard.seccio_cap')}
                      </div>
                    )}
                    {grup.items.map(({ p, idx }) => {
                  const conf = (p.confidence || '').toUpperCase()
                  const low = conf === 'LOW' || conf === 'NO_MATCH'
                  const med = conf === 'MEDIUM'
                  const noMatch = !p.pom_master_id
                  const tenantOnly = noMatch && !!p.tenant_only
                  // QA-S8 · PENDENT: el backend ha trobat alguna cosa però NO l'ha vinculada
                  // (confiança baixa, o dues files de la fitxa apuntant al mateix POM). No és
                  // un "sense match": és un suggeriment que espera una decisió humana, i s'ha
                  // de veure com a tal — si no, la persona no sap què li estan proposant.
                  const pendent = noMatch && !!p.weak_suggestion && !tenantOnly
                  // R3 · l'estat de la fila davant del conflicte: `res` és la decisió presa i
                  // encara no enviada; `conflicte` és el que el backend n'ha dit.
                  const res = resolucions[p.ordre]
                  const conflicte = conflictes[p.ordre]
                  return (
                    <Fragment key={idx}>
                    {/* `data-fila` — l'àncora de la fila per a l'arnès de captura, i el mateix
                        patró que `EditableTable` ja fa servir (`data-fila`, `data-pindola`):
                        sense ella, una passejada ha de comptar píndoles per posició i qualsevol
                        canvi de columnat li mou la tria a una altra fila. */}
                    <div ref={el => { filaRefs.current[p.ordre] = el }} data-fila={p.ordre} style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                      borderTop: idx ? `1px solid ${BORDER}` : 'none',
                      background: conflicte ? 'var(--err-bg)' : res ? 'var(--ok-bg)'
                        : !p.actiu ? 'var(--bg-card)' : tenantOnly ? '#f3f0fb' : low ? '#fdf3ee' : 'var(--white)',
                      opacity: p.actiu ? 1 : 0.55,
                    }}>
                      <input type="checkbox" checked={!!p.actiu}
                        onChange={() => res ? treuResolucio(p.ordre)
                          : noMatch ? obrePanell(p) : togglePom(idx)} />
                      <div style={{ flex: '0 0 90px', fontWeight: 600, fontSize: 'var(--fs-body)' }}>
                        {p.codi_fitxa || '—'}
                      </div>
                      <div style={{ fontSize: 'var(--fs-h3)', color: 'var(--text-muted)' }}>→</div>
                      <div style={{ flex: 1, fontSize: 'var(--fs-body)' }}>
                        {res
                          ? <span style={{ color: 'var(--ok)' }}>
                              {res.accio === 'vincula'
                                ? t('import_wizard.resol_fet_vincula', { codi: res.pom_codi, nom: res.pom_nom })
                                : t('import_wizard.resol_fet_crea', { codi: res.codi, nom: res.nom })}
                              <b>{sufixIdentitat(filaAmbIdentitat(p, identitats), dicc, lang)}</b>
                            </span>
                          : noMatch
                          ? (tenantOnly
                              ? <span style={{ color: '#5b3fa3' }}>
                                  {p.descripcio || t('import_wizard.no_description')}
                                  <span style={{ marginLeft: 8, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                                    {t('import_wizard.will_add_tenant')}
                                  </span>
                                </span>
                              : <span style={{ color: pendent ? 'var(--gold)' : '#a32d2d' }}>
                                  {pendent
                                    ? t('import_wizard.pending_review')
                                    : t('import_wizard.no_match')} — {p.descripcio || t('import_wizard.no_description')}
                                  {pendent && (
                                    <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                                      {p.many_to_one
                                        ? t('import_wizard.many_to_one_hint', { codi: p.weak_suggestion_codi })
                                        : t('import_wizard.weak_hint')}
                                      {' '}<b>{p.weak_suggestion_codi}</b> · {p.weak_suggestion}
                                    </div>
                                  )}
                                  {/* «Afegir com a propi» passa per la MATEIXA via que la
                                      resta: obre el panell amb codi i nom editables, i el que
                                      s'envia és una resolució 'crea', no el codi a cegues. */}
                                  <span onClick={() => obrePanell(p)}
                                    style={{ marginLeft: 8, fontSize: 'var(--fs-body)', color: GOLD,
                                             cursor: 'pointer', textDecoration: 'underline' }}>
                                    {t('import_wizard.add_as_own')}
                                  </span>
                                </span>)
                          : <><b>{p.pom_codi}</b> · {p.pom_nom || p.descripcio}
                              {/* P2-ter · LA FILA INFORMA. La instància entra al NOM, com a la
                                  graella del pas 3 i com a la fitxa: aquí es LLEGEIX què és
                                  aquesta fila. Per canviar-la, «canvia el vincle» — l'edició viu
                                  al panell. I el que es llegeix és la decisió PENDENT, no
                                  l'últim desat: si no, diria «única» just després que algú hagi
                                  triat «Bottom». */}
                              <b>{sufixIdentitat(filaAmbIdentitat(p, identitats), dicc, lang)}</b>
                            </>}
                      </div>
                      {/* Qualsevol fila es pot re-decidir, tingui match o no. */}
                      <button type="button" onClick={() => obrePanell(p)}
                        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                                 fontSize: 'var(--fs-label)', color: GOLD, textDecoration: 'underline',
                                 fontFamily: 'inherit', whiteSpace: 'nowrap' }}>
                        {t('import_wizard.resol_canvia')}
                      </button>
                      <span style={{
                        fontSize: 'var(--fs-body)', fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                        background: conflicte ? 'var(--err-bg)' : res ? 'var(--ok-bg)'
                          : tenantOnly ? '#ede7fb' : pendent ? '#fdf6ee' : noMatch ? '#fff0f0' : (low || med) ? '#fdf6ee' : '#f0f9f0',
                        color: conflicte ? 'var(--err)' : res ? 'var(--ok)'
                          : tenantOnly ? '#5b3fa3' : pendent ? 'var(--gold)' : noMatch ? '#a32d2d' : (low || med) ? 'var(--gold)' : '#3b6d11',
                      }}>{conflicte ? t('import_wizard.resol_badge_conflicte')
                          : res ? t('import_wizard.resol_badge_resolt')
                          : tenantOnly ? 'tenant-only'
                          : pendent ? t('import_wizard.pending_badge')
                          : noMatch ? t('import_wizard.no_match_badge') : conf.toLowerCase()}</span>
                      {/* ═══ SET-2/T8-ter · LA COLUMNA DE PEÇA · A LA DRETA DE TOT ═══
                          La fila es llegeix codi → vincle → accions, i aquesta és l'última
                          pregunta: DE QUI és. Sempre visible i mai al panell, i no és una
                          excepció a P2-ter sinó una natura de dada diferent — capa i instància
                          són eixos de GERMANOR (matisos d'una mesura, es responen mirant-la de
                          prop) i la peça és una FRONTERA (pertinença, es respon escanejant la
                          COLUMNA sencera). L'argument sencer viu a `filaPas2.js`, que és on
                          les dues lleis es toquen.

                          TRES ESTATS, i el que els distingeix no és decoració: verd = algú ho
                          ha DECIDIT · àmbar = el document ho PROPOSA i espera un clic · neutre
                          = ningú ho ha mirat i anirà a la peça de la sessió. «Ningú no ho ha
                          mirat» i «algú ha dit que és de la mare» no són el mateix estat.
                          La regla és `estatDeLaPeca`, i es prova amb `node --test`. */}
                      {peces.length > 0 && (() => {
                        const estat = estatDeLaPeca(p, identitats)
                        const visible = pecaVisible(p, identitats, garment || '')
                        const COL = { decidit: { bg: '#f0f9f0', fg: '#3b6d11', br: '#cfe6c0' },
                                      proposat: { bg: '#fdf6ee', fg: 'var(--gold)', br: 'var(--gold-border)' },
                                      defecte: { bg: 'var(--white)', fg: 'var(--text-muted)', br: BORDER } }[estat]
                        return (
                          <select
                            data-peca={p.ordre} data-estat={estat}
                            value={visible}
                            title={estat === 'proposat'
                              ? t('import_wizard.peca_proposada_tip', { seccio: p.seccio || '' })
                              : t('import_wizard.peca_tip')}
                            aria-label={t('import_wizard.peca_col')}
                            onChange={e => setIdentitats(prev => ({
                              ...prev,
                              [p.ordre]: { ...(prev[p.ordre] || {}), garment: e.target.value },
                            }))}
                            style={{
                              flex: '0 0 auto', minWidth: 116, maxWidth: 160, padding: '2px 6px',
                              borderRadius: 6, fontFamily: 'inherit', fontSize: 'var(--fs-label)',
                              background: COL.bg, color: COL.fg, border: `1px solid ${COL.br}`,
                              fontWeight: estat === 'defecte' ? 400 : 600,
                            }}>
                            {peces.map(pc => (
                              <option key={pc.codi} value={pc.codi}>
                                {pc.es_mare ? t('resum_wizard.model_base') : (pc.nom || pc.codi)}
                              </option>
                            ))}
                          </select>
                        )
                      })()}
                    </div>
                    {panellOrdre === p.ordre && (
                      <ResolPanel
                        fila={p} conflicte={conflicte} res={res} modelId={model.id}
                        crea={crea} setCrea={setCrea}
                        onTanca={() => setPanellOrdre(null)}
                        dicc={dicc}
                        capa={capaEfectiva(p, identitats)}
                        instancia={instanciaEfectiva(p, identitats)}
                        onCapa={slug => setIdentitats(prev => ({
                          ...prev, [p.ordre]: { ...identitatEfectiva(p, prev), capa: slug } }))}
                        onInstancia={slug => setIdentitats(prev => ({
                          ...prev, [p.ordre]: { ...identitatEfectiva(p, prev), instancia: slug } }))}
                        onVincula={(c) => posaResolucio(p.ordre, {
                          accio: 'vincula', pom_master_id: c.id,
                          pom_codi: c.codi_client, pom_nom: c.nom_client,
                        }, { tanca: false })}
                        onCrea={() => posaResolucio(p.ordre, {
                          accio: 'crea', codi: crea.codi.trim(),
                          nom: crea.nom.trim() || crea.codi.trim(),
                        }, { tanca: false })}
                      />
                    )}
                    </Fragment>
                  )
                    })}
                  </Fragment>
                ))}
              </div>

              {/* Afegir POM manual del catàleg */}
              <div style={{ marginBottom: 16 }}>
                {!showAddPom ? (
                  <button type="button" onClick={() => setShowAddPom(true)}
                    style={{ padding: '6px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
                             border: `1px dashed ${GOLD}`, background: 'transparent', color: GOLD }}>
                    {t('import_wizard.add_pom_catalog')}
                  </button>
                ) : (
                  <PomCatalegPicker modelId={model.id} autoFocus onPick={addPomManual} />
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button type="button" onClick={() => setStep(1)}
                  style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                           background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
                  ← {t('app.back')}
                </button>
                <button type="button" onClick={handleContinuePoms} disabled={pomsActius === 0 || savingPoms}
                  style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                           fontWeight: 500, color: 'var(--white)',
                           background: pomsActius && !savingPoms ? GOLD : '#ccc',
                           cursor: pomsActius && !savingPoms ? 'pointer' : 'not-allowed' }}>
                  {t('import_wizard.continue_measures')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════ PAS 3 — MESURES ═══════════════ */}
      {step === 3 && (
        <div>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 10 }}>
            {t('import_wizard.table_intro', { poms: pomsTaula.length, sizes: tallesSel.length, base: baseSize })}
          </div>

          {/* 1C-2b — com estan expressats els valors de la fitxa (default suggerit per l'heurística) */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button type="button" onClick={() => setValorsMode('absoluts')}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: valorsMode === 'absoluts' ? GOLD : '#f5f0ea',
                         color: valorsMode === 'absoluts' ? 'var(--white)' : 'var(--text-muted)' }}>{t('import_wizard.absolute_measures')}</button>
              <button type="button" onClick={() => setValorsMode('deltes')}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: valorsMode === 'deltes' ? GOLD : '#f5f0ea',
                         color: valorsMode === 'deltes' ? 'var(--white)' : 'var(--text-muted)' }}>{t('import_wizard.increments')}</button>
            </div>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 5 }}>
              {t('import_wizard.values_help')}{valorsMode === 'deltes'
                ? t('import_wizard.values_help_deltes') : ''}
            </div>
          </div>

          {emptyCols.length > 0 && (
            <div style={{ background: '#fdf6ee', border: '1px solid var(--gold-border)', color: 'var(--gold)',
                          borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 10,
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <span>{t('import_wizard.sizes_no_values')} <b>{emptyCols.join(', ')}</b>.</span>
              <button type="button" onClick={handleGenerarGrading} disabled={gradingLoading || !baseTeValors}
                title={baseTeValors ? '' : t('import_wizard.need_base_values')}
                style={{ padding: '6px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', whiteSpace: 'nowrap',
                         border: `1px solid ${GOLD}`, background: 'transparent', color: GOLD,
                         cursor: baseTeValors && !gradingLoading ? 'pointer' : 'not-allowed' }}>
                {gradingLoading ? t('import_wizard.generating') : t('import_wizard.generate_grading')}
              </button>
            </div>
          )}

          <div style={{ overflowX: 'auto', border: `1px solid ${BORDER}`, borderRadius: 8, marginBottom: 16 }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 'var(--fs-body)' }}>
              <thead>
                <tr style={{ background: '#f5f0ea' }}>
                  <th style={{ padding: '8px 10px', textAlign: 'left', position: 'sticky', left: 0,
                               background: '#f5f0ea', minWidth: 160 }}>POM</th>
                  {tallesSel.map(talla => (
                    <th key={talla} style={{ padding: '8px 10px', textAlign: 'center', minWidth: 64,
                          background: talla === baseSize ? '#f0e7cf' : '#f5f0ea',
                          color: talla === baseSize ? '#7a5a00' : 'var(--text-main)' }}>
                      {talla}{talla === baseSize && <div style={{ fontSize: 'var(--fs-caption)' }}>{t('import_wizard.col_base')}</div>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {grupsTaula.map((grup, gi) => (
                  <Fragment key={`g${gi}`}>
                    {(grup.seccio || taulaAmbSeccions) && (
                      <tr>
                        <td colSpan={1 + tallesSel.length} style={{ ...SUBHEAD, borderTop: `1px solid ${BORDER}` }}>
                          {grup.seccio || t('import_wizard.seccio_cap')}
                        </td>
                      </tr>
                    )}
                    {/* P1 · la `key` de la fila és l'ORDRE. Amb el POM, dues germanes (el
                        mateix POM en dues instàncies) donaven claus DUPLICADES: React
                        desmunta i remunta els inputs i el que s'està teclejant es perd.
                        L'`ordre` el fixa l'extracció i no canvia entre renders. */}
                    {grup.items.map(p => (
                  <tr key={p.ordre} style={{ borderTop: `1px solid ${BORDER}` }}>
                    <td style={{ padding: '6px 10px', position: 'sticky', left: 0, background: 'var(--white)' }}>
                      {/* QA-S8 · El codi del DOCUMENT mana: és el que la persona té al paper
                          davant. El del catàleg queda com a secundari i atenuat, i només si
                          difereix. Abans manava el del catàleg i la fitxa deia 'A' mentre la
                          pantalla deia 'CH': no hi havia manera de relacionar-les.
                          Coherent amb el pas 2 (:681) i amb MeasureGrid (nom_fitxa || pom_code). */}
                      <b>{p.codi_fitxa || p.pom_codi}</b>
                      {p.pom_codi && p.codi_fitxa && p.pom_codi !== p.codi_fitxa && (
                        <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> → {p.pom_codi}</span>
                      )}
                      {/* P3 · LA IDENTITAT AL RÈTOL, no en una columna nova: el que eixampla
                          una taula és el rètol, i aquí la instància és el que fa que dues
                          files del mateix POM es puguin dir l'una de l'altra. Mateix ordre i
                          mateixa forma que a la fitxa i a MeasureGrid (` · Bottom · Folre`). */}
                      <span style={{ fontWeight: 500 }}>{sufixIdentitat(p, dicc, lang)}</span>
                      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>{p.pom_nom || p.descripcio}</div>
                    </td>
                    {tallesSel.map(talla => (
                      <td key={talla} style={{ padding: '2px', textAlign: 'center',
                            background: talla === baseSize ? '#fbf7ec' : 'var(--white)' }}>
                        <input type="number" step="0.1"
                          value={taula[p.ordre]?.[talla] ?? ''}
                          onChange={e => setCell(p.ordre, talla, e.target.value)}
                          style={{ width: 56, padding: '4px', textAlign: 'center', fontSize: 'var(--fs-body)',
                                   border: `1px solid ${BORDER}`, borderRadius: 4,
                                   fontFamily: 'inherit' }} />
                      </td>
                    ))}
                  </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(2)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              ← {t('app.back')}
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={goCrearLibrary} disabled={!baseTeValors || savingMesures}
                title={baseTeValors ? t('import_wizard.create_library_title')
                                    : t('import_wizard.base_needs_value')}
                style={{ padding: '8px 16px', borderRadius: 6, border: `1px solid ${GOLD}`,
                         background: 'transparent', color: GOLD, fontSize: 'var(--fs-body)',
                         cursor: baseTeValors && !savingMesures ? 'pointer' : 'not-allowed' }}>
                {t('import_wizard.create_library')}
              </button>
              <button type="button" onClick={handleContinueMesures} disabled={!baseTeValors || savingMesures}
                title={baseTeValors ? '' : t('import_wizard.base_needs_value')}
                style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                         fontWeight: 500, color: 'var(--white)',
                         background: baseTeValors && !savingMesures ? GOLD : '#ccc',
                         cursor: baseTeValors && !savingMesures ? 'pointer' : 'not-allowed' }}>
                {t('import_wizard.continue_fabric')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 4 — TEIXIT ═══════════════ */}
      {step === 4 && (
        <div>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
            {t('import_wizard.fabric_and_shrinkage')} <b>{t('import_wizard.optional')}</b> {t('import_wizard.skip_step_hint')}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            <div>
              <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>{t('import_wizard.fabric_main_label')}</label>
              <input value={teixit.fabric_main}
                onChange={e => setTeixit(prev => ({ ...prev, fabric_main: e.target.value }))}
                placeholder={t('import_wizard.fabric_main_ph')}
                style={{ width: '100%', padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6,
                         border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>
            <div>
              <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>{t('import_wizard.composition')}</label>
              <input value={teixit.fabric_composition}
                onChange={e => setTeixit(prev => ({ ...prev, fabric_composition: e.target.value }))}
                placeholder={t('import_wizard.composition_ph')}
                style={{ width: '100%', padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6,
                         border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {t('import_wizard.shrinkage_iso')}
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {isoTable.map(entry => {
                const active = teixit.shrinkage_type === 'ISO' && teixit.shrinkage_iso_key === entry.id
                return (
                  <button key={entry.id} type="button" onClick={() => selectIso(entry)}
                    style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
                             border: active ? `1.5px solid ${GOLD}` : `0.5px solid ${BORDER}`,
                             background: active ? '#fdf6ee' : 'transparent', color: 'var(--text-muted)' }}>
                    {entry.nom} <span style={{ fontSize: 'var(--fs-body)' }}>{entry.warp}%/{entry.weft}%</span>
                  </button>
                )
              })}
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <button type="button" onClick={() => setBiaxial(true)}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: biaxial ? GOLD : '#f5f0ea', color: biaxial ? 'var(--white)' : 'var(--text-muted)' }}>Warp / Weft</button>
              <button type="button" onClick={() => setBiaxial(false)}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: !biaxial ? GOLD : '#f5f0ea', color: !biaxial ? 'var(--white)' : 'var(--text-muted)' }}>Single %</button>
            </div>
            {biaxial ? (
              <div style={{ display: 'flex', gap: 12 }}>
                <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_warp}
                  onChange={e => setTeixit(t => ({ ...t, shrinkage_warp: e.target.value, shrinkage_type: 'SUPPLIER', shrinkage_iso_key: '' }))}
                  placeholder="Warp %" style={{ width: 90, padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
                <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_weft}
                  onChange={e => setTeixit(t => ({ ...t, shrinkage_weft: e.target.value, shrinkage_type: 'SUPPLIER', shrinkage_iso_key: '' }))}
                  placeholder="Weft %" style={{ width: 90, padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
              </div>
            ) : (
              <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_pct}
                onChange={e => setTeixit(t => ({ ...t, shrinkage_pct: e.target.value, shrinkage_type: 'SUPPLIER' }))}
                placeholder="Shrinkage %" style={{ width: 110, padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>{t('import_wizard.notes')}</label>
            <textarea value={teixit.fabric_notes} rows={2}
              onChange={e => setTeixit(t => ({ ...t, fabric_notes: e.target.value }))}
              style={{ width: '100%', padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, resize: 'vertical',
                       border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(3)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>← {t('app.back')}</button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => handleSaveTeixit(true)} disabled={savingTeixit}
                style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                         background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>{t('import_wizard.skip')}</button>
              <button type="button" onClick={() => handleSaveTeixit(false)} disabled={savingTeixit}
                style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)', fontWeight: 500,
                         color: 'var(--white)', background: GOLD, cursor: 'pointer' }}>{t('import_wizard.continue_save')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 5 — GUARDAR ═══════════════ */}
      {step === 5 && (
        <div>
          <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('import_wizard.summary_title')}</div>
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
            {[
              [t('import_wizard.target_model'), `${model.codi_intern} · ${model.nom_prenda || ''}`],
              [t('import_wizard.step.sizes'), `${tallesSel.length} (${tallesSel.join('·')})`],
              [t('import_wizard.step.poms'), t('import_wizard.confirmed_count', { count: pomsActius })],
              [t('import_wizard.measure_values'), `${nValors}`],
              [t('import_wizard.step.fabric'), teixitInformat ? (teixit.fabric_main || t('import_wizard.fabric_informed')) : t('import_wizard.fabric_not_informed')],
            ].map(([k, v], i) => (
              <div key={k} style={{ display: 'flex', padding: '8px 12px', fontSize: 'var(--fs-body)',
                                    borderTop: i ? `1px solid ${BORDER}` : 'none' }}>
                <div style={{ flex: '0 0 160px', color: 'var(--text-muted)' }}>{k}</div>
                <div style={{ flex: 1, fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#f0f9f0', border: '1px solid #c0dd97', color: '#3b6d11',
                        borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 16 }}>
            {t('import_wizard.mana_doc', { count: pomsActius })}
          </div>

          {/* ── SET-2/T8-ter (16/08) · AQUÍ HI HAVIA L'AVÍS DE MULTI-PRENDA I S'HA RETIRAT.
              Deia «aquest document sembla portar més d'una peça; tot anirà a X» — i era el que
              es podia dir mentre l'import fos d'UNA peça i el destí ja estigués decidit: un avís
              perquè ningú es trobés la feina en un lloc que no esperava.

              Amb la columna del pas 2 la frase ha deixat de ser certa (ja no va tot a X) i,
              sobretot, ha deixat de ser NECESSÀRIA: el suggeriment ja no interromp al final del
              camí, es pinta AL LLOC DE LA DECISIÓ —les files de la secció SHORT surten en àmbar
              a la seva columna— i confirmar-lo és un clic allà mateix. Un avís que repetís al
              pas 5 el que la columna ja diu al pas 2 només afegiria una lectura.

              La DADA es conserva (`cribratge.mes_duna_prenda`, i el backend segueix desant-la a
              `resultat['mes_duna_prenda']`): és traça del que el document deia, i el dia que la
              proposta falli servirà per saber que el senyal hi era. */}

          {/* PRINCIPI DEL SOROLL — el model s'alimenta de realitat. Les mesures vives que el
              document NO menciona es PROPOSEN per desactivar; mai s'esborren soles i mai
              sobreviuen actives en silenci. Sempre soft-delete (el model en guarda memòria). */}
          {sorollConflict && (
            <div style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                          padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600,
                            fontSize: 'var(--fs-body)', color: '#7a5a00', marginBottom: 6 }}>
                <i className="ti ti-eraser" aria-hidden="true" />
                {t('import_wizard.soroll_title')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 10 }}>
                {t('import_wizard.soroll_help', { count: sorollConflict.n })}
              </div>
              <ul style={{ margin: '0 0 12px', paddingLeft: 18, fontSize: 'var(--fs-label)',
                           color: 'var(--text-muted)', maxHeight: 160, overflowY: 'auto' }}>
                {(sorollConflict.poms || []).map(p => (
                  <li key={p.pom_id} style={{ marginBottom: 2 }}>
                    <strong style={{ color: 'var(--text-main)' }}>{p.codi || `#${p.pom_id}`}</strong>
                    {p.nom ? ` · ${p.nom}` : ''}
                    {p.base_value_cm != null ? ` · ${p.base_value_cm} cm` : ''}
                    {p.origen ? ` · ${p.origen}` : ''}
                  </li>
                ))}
              </ul>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => handleConfirmar({ poda_choice: 'desactivar' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-body)',
                           fontWeight: 500, color: 'var(--white)', background: GOLD,
                           cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.soroll_desactivar')}
                </button>
                <button type="button" onClick={() => handleConfirmar({ poda_choice: 'conservar' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: `0.5px solid ${BORDER}`,
                           fontSize: 'var(--fs-body)', fontWeight: 500, background: 'var(--white)',
                           color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.soroll_conservar')}
                </button>
              </div>
            </div>
          )}

          {/* PRECEDÈNCIA MÍNIMA D'ORÍGENS — el document no trepitja el que un tècnic va
              escriure a mà sense demanar-ho. Mateixa mecànica de proposta+confirmació. */}
          {manualConflict && (
            <div style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                          padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600,
                            fontSize: 'var(--fs-body)', color: '#7a5a00', marginBottom: 6 }}>
                <i className="ti ti-hand-stop" aria-hidden="true" />
                {t('import_wizard.soroll_manual_title')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 10 }}>
                {t('import_wizard.soroll_manual_help', { count: manualConflict.n })}
              </div>
              <ul style={{ margin: '0 0 12px', paddingLeft: 18, fontSize: 'var(--fs-label)',
                           color: 'var(--text-muted)', maxHeight: 160, overflowY: 'auto' }}>
                {(manualConflict.poms || []).map(p => (
                  <li key={p.pom_id} style={{ marginBottom: 2 }}>
                    <strong style={{ color: 'var(--text-main)' }}>{p.codi || `#${p.pom_id}`}</strong>
                    {p.nom ? ` · ${p.nom}` : ''}
                    {' · '}{p.valor_manual} cm → {p.valor_document} cm
                  </li>
                ))}
              </ul>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => handleConfirmar({ manual_choice: 'sobreescriure' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-body)',
                           fontWeight: 500, color: 'var(--white)', background: GOLD,
                           cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.soroll_manual_sobreescriure')}
                </button>
                <button type="button" onClick={() => handleConfirmar({ manual_choice: 'respectar' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: `0.5px solid ${BORDER}`,
                           fontSize: 'var(--fs-body)', fontWeight: 500, background: 'var(--white)',
                           color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.soroll_manual_respectar')}
                </button>
              </div>
            </div>
          )}

          {/* Llei del contenidor — combinació verge: el client no té contenidor per aquesta
              (peça + sistema de talles + fit). Crear-lo (acte explícit) o deixar el model amb
              residents i prou (sobirania). MAI creació silenciosa. */}
          {containerConflict && (
            <div style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                          padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600,
                            fontSize: 'var(--fs-body)', color: '#7a5a00', marginBottom: 6 }}>
                <i className="ti ti-package" aria-hidden="true" />
                {t('import_wizard.container_absent_title')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 10 }}>
                {t('import_wizard.container_absent_help', {
                  customer: containerConflict.customer_nom || '',
                  item: containerConflict.garment_type_item || '',
                  size_system: containerConflict.size_system || '',
                  fit: containerConflict.fit || '',
                })}
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => handleConfirmar({ container_choice: 'create' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-body)',
                           fontWeight: 500, color: 'var(--white)', background: GOLD,
                           cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.container_create')}
                </button>
                <button type="button" onClick={() => handleConfirmar({ container_choice: 'no_container' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: `0.5px solid ${BORDER}`,
                           fontSize: 'var(--fs-body)', fontWeight: 500, background: 'var(--white)',
                           color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.container_skip')}
                </button>
              </div>
            </div>
          )}

          {/* Llei del contenidor — conflicte per-regla: la fitxa contradiu el catàleg del client.
              Per a cada POM: mantenir catàleg / actualitzar-lo / deixar-lo resident-només al model. */}
          {gradingConflict && (
            <div style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                          padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600,
                            fontSize: 'var(--fs-body)', color: '#7a5a00', marginBottom: 6 }}>
                <i className="ti ti-alert-triangle" aria-hidden="true" />
                {t('import_wizard.grading_conflict_title')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 8 }}>
                {t('import_wizard.grading_conflict_help')}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10, alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
                  {t('import_wizard.conflict_apply_all')}:
                </span>
                {['keep_catalog', 'update_catalog', 'model_resident'].map(opt => (
                  <button key={opt} type="button" disabled={confirming}
                    onClick={() => {
                      const all = {}
                      for (const d of (gradingConflict.divergencies || [])) all[d.pom_id] = opt
                      setConflictChoices(all)
                    }}
                    style={{ padding: '3px 10px', borderRadius: 12, border: `0.5px solid ${BORDER}`,
                             background: 'var(--white)', fontSize: 'var(--fs-caption)',
                             color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                    {t(`import_wizard.conflict_${opt}`)}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                {(gradingConflict.divergencies || []).map(d => (
                  <div key={d.pom_id} style={{ borderTop: `0.5px solid ${BORDER}`, paddingTop: 8 }}>
                    <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{d.pom}</div>
                    <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginBottom: 6 }}>{d.detall}</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {['keep_catalog', 'update_catalog', 'model_resident'].map(opt => {
                        const active = conflictChoices[d.pom_id] === opt
                        return (
                          <button key={opt} type="button" disabled={confirming}
                            onClick={() => setConflictChoices(prev => ({ ...prev, [d.pom_id]: opt }))}
                            style={{ padding: '4px 10px', borderRadius: 6,
                                     border: `${active ? '1px' : '0.5px'} solid ${active ? GOLD : BORDER}`,
                                     background: active ? '#fffdf5' : 'var(--white)',
                                     fontWeight: active ? 600 : 500, fontSize: 'var(--fs-caption)',
                                     color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                            {t(`import_wizard.conflict_${opt}`)}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
              <button type="button" disabled={confirming}
                onClick={() => handleConfirmar({ conflict_resolutions: conflictChoices })}
                style={{ padding: '8px 16px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-body)',
                         fontWeight: 600, color: 'var(--white)', background: GOLD,
                         cursor: confirming ? 'not-allowed' : 'pointer' }}>
                {t('import_wizard.conflict_apply')}
              </button>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(4)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>← {t('app.back')}</button>
            <button type="button" onClick={() => handleConfirmar()} disabled={confirming || !!gradingConflict || !!containerConflict}
              style={{ padding: '8px 24px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)', fontWeight: 600,
                       color: 'var(--white)', background: (confirming || gradingConflict || containerConflict) ? '#ccc' : GOLD,
                       cursor: (confirming || gradingConflict || containerConflict) ? 'not-allowed' : 'pointer' }}>
              {confirming ? t('import_wizard.confirming') : t('import_wizard.confirm_save')}
            </button>
          </div>
        </div>
      )}

      {confirmSizeMap && (
        <Modal
          title={t('import_wizard.configure_run_title')}
          confirmLabel={t('import_wizard.go_to_library')}
          cancelLabel={t('app.cancel')}
          onCancel={() => setConfirmSizeMap(false)}
          onConfirm={() => { setConfirmSizeMap(false); goConfigureRun() }}
        >
          <p style={{ fontSize: 'var(--fs-body)', color: '#444', lineHeight: 1.5 }}>
            {t('import_wizard.modal_body')}
          </p>
        </Modal>
      )}
    </div>
  )
}
