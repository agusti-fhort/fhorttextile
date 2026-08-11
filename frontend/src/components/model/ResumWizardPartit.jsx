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
import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import CascadeFinder from '../CascadeSelector/CascadeFinder'
import CustomerSelector from '../CustomerSelector'
import { useEixos } from '../grading/eixosFont'
import RuleSetPicker from '../grading/RuleSetPicker'
import useConfirmacioRuleset from './useConfirmacioRuleset'
import { models, sizeSystems, gradingRuleSets, garmentGroups, customers } from '../../api/endpoints'
import PecaDefinicioContenidor, { BotoCanviar, FilaDefinicio, ValorCamp }
  from './PecaDefinicioContenidor'
import { ORIGEN, origenDeLaFila } from '../../utils/pecaDefinicio'
import { ordenaPerProximitat } from '../../utils/proximitatRun'
import { labelsOf, ordenaPelSistema } from '../../utils/talles'
import Feedback from '../ui/Feedback'
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
  // peça que l'hereta, i el contracte només el resol al servidor.
  useEffect(() => {
    if (!id) return
    let viu = true
    models.peces(id)
      .then(r => { if (viu) setPeces(r.data?.peces || []) })
      // Una llista buida no és cap avaria visible: sense peces, la definició es pinta com
      // sempre s'ha pintat. El que no pot passar és que la pantalla peti per això.
      .catch(() => { if (viu) setPeces([]) })
    return () => { viu = false }
  }, [id, model])

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
            <PecaDefinicioContenidor key={peca.codi || 'base'} peca={peca} fet={fets === 3}>
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
                <FilesDeLaPeca model={model} peca={peca} />
              )}
            </PecaDefinicioContenidor>
          ))}
        </div>
      </div>
    </>
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
// El «Canviar» hi és i està APAGAT: la porta d'escriptura d'una peça encara no existeix, i un
// botó viu que no desa és pitjor que un d'apagat.
function FilesDeLaPeca({ model, peca }) {
  const { t } = useTranslation()
  const cap = t('resum_wizard.no_value')
  const gt = [model.garment_type_nom, model.garment_type_item_nom].filter(Boolean).join(' · ')
  return (
    <>
      {/* Fixa, apagada i sense acció: la peça no pot canviar això mai. */}
      <FilaDefinicio etiqueta={t('resum_wizard.step_piece')} origen={ORIGEN.DEL_MODEL}>
        <span>
          {[model.target && t(`model_wizard.target_${model.target}`, model.target),
            model.construction && t(`model_wizard.construction_${model.construction}`, model.construction),
            model.fit_type && t(`model_wizard.fit_${model.fit_type}`, model.fit_type)]
            .filter(Boolean).join(' · ')}
        </span>
        {gt ? <div style={{ marginTop: 2 }}>{gt}</div> : null}
      </FilaDefinicio>

      <FilaDefinicio etiqueta={t('resum_wizard.step_sizes')}
        origen={origenDeLaFila(peca.size_run_model)}
        accio={<BotoCanviar disabled>{t('resum_wizard.change')}</BotoCanviar>}>
        <div><ValorCamp camp={peca.size_system} buit={cap} /></div>
        <div style={{ marginTop: 4 }}>
          <ValorCamp camp={peca.size_run_model} buit={cap} />
          {peca.base_size_label?.etiqueta
            ? <span style={{ marginLeft: 8, color: 'var(--text-soft)' }}>
                {peca.base_size_label.etiqueta} · {t('resum_wizard.base')}
              </span>
            : null}
        </div>
      </FilaDefinicio>

      <FilaDefinicio etiqueta={t('resum_wizard.step_grading')}
        origen={origenDeLaFila(peca.grading_rule_set)}
        accio={<BotoCanviar disabled>{t('resum_wizard.change')}</BotoCanviar>}>
        <ValorCamp camp={peca.grading_rule_set} buit={cap} />
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
          // tipus de peça escrit. Res s'amaga en tancar-se.
          <div>
            <span style={retolCamp}>{t('resum_wizard.axes')}</span>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
              {model.target && <Xip marcat disabled>{t(`model_wizard.target_${model.target}`, model.target)}</Xip>}
              {model.construction && <Xip marcat disabled>{t(`model_wizard.construction_${model.construction}`, model.construction)}</Xip>}
              {model.fit_type && <Xip marcat disabled>{t(`model_wizard.fit_${model.fit_type}`, model.fit_type)}</Xip>}
            </div>
            <div style={{ marginTop: 8 }}>
              <span style={retolCamp}>{t('resum_wizard.piece_type')}</span><br />
              <b>{model.garment_type_nom}</b>
              {model.garment_type_item_nom && ` · ${model.garment_type_item_nom}`}
            </div>
          </div>
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

// ── DRETA · PAS 3 · TALLES ────────────────────────────────────────────────────────────────
function PasTalles({ model, estat, onObrir, desa, onCancel }) {
  const { t } = useTranslation()
  const obert = estat === 'ara'
  const [systems, setSystems] = useState([])
  const [sel, setSel] = useState(null)
  const [run, setRun] = useState([])
  const [base, setBase] = useState(null)
  const [desant, setDesant] = useState(false)

  // EL CODI DEL CLIENT del model. El detall no el porta (només `customer_nom`) i la
  // proximitat el necessita: sense ell, el run DEL CLIENT d'aquest model no pot anar primer i
  // la llista queda ordenada com si el model no fos de ningú (el parany del model 174).
  const [codiClient, setCodiClient] = useState(null)
  //
  // SET-2/T7-B5 — I NOMÉS AMB EL SUBESPAI OBERT. Aquest codi només serveix per ORDENAR els runs
  // candidats en el moment de triar-ne un: amb el pas tancat no hi ha cap llista a ordenar, i la
  // crida es feia igualment a cada fitxa de model que s'obria. El pas tancat pinta el run que el
  // model ja té, que ve al detall i no necessita ningú.
  const obertTalles = estat === 'ara'
  useEffect(() => {
    if (!obertTalles || !model.customer) { setCodiClient(null); return undefined }
    let viu = true
    customers.get(model.customer)
      .then(r => { if (viu) setCodiClient(r.data?.codi ?? null) })
      .catch(() => { if (viu) setCodiClient(null) })
    return () => { viu = false }
  }, [obertTalles, model.customer])

  // Triar un sistema NO substitueix el run en silenci: si el que el model té hi cap, es
  // conserva (i amb ell la talla base). És la mateixa llei F1.2 del wizard.
  const triaSistema = (s, rehidratant = false) => {
    setSel(s)
    const labels = labelsOf(s)
    const desat = (model.size_run_model || '').split(/[·,;]/).map(x => x.trim()).filter(Boolean)
    const conserva = rehidratant && desat.length && desat.every(l => labels.includes(l))
    const nou = conserva ? desat : labels
    setRun(nou)
    setBase(conserva && model.base_size_label && nou.includes(model.base_size_label)
      ? model.base_size_label
      : (nou[Math.floor(nou.length / 2)] || nou[0] || null))
  }

  // Els sistemes s'ORDENEN PER PROXIMITAT i NO S'AMAGA CAP (D-31.3 · `utils/proximitatRun`,
  // el mateix mòdul que el pas 3 del wizard). El run del client d'aquest model, primer.
  useEffect(() => {
    if (!obert) return undefined
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
        const seu = rows.find(s => s.id === model.size_system)
        if (seu) triaSistema(seu, true)
      })
      .catch(() => { if (viu) setSystems([]) })
    return () => { viu = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [obert, model.size_system, codiClient])

  const toggleTalla = (label) => setRun(prev => (
    prev.includes(label) ? prev.filter(x => x !== label) : ordenaPelSistema([...prev, label], labelsOf(sel))
  ))

  const valid = !!(sel && run.length > 0 && base && run.includes(base))
  const desar = async () => {
    setDesant(true)
    await desa({ size_system_id: sel.id, size_run: run.join('·'), base_size: base },
      'resum_wizard.sizes_saved')
    setDesant(false)
  }

  if (!obert) {
    return (
      <FilaDefinicio etiqueta={t('resum_wizard.step_sizes')}
        accio={estat === 'fet'
          ? <BotoCanviar onClick={onObrir}>{t('resum_wizard.change')}</BotoCanviar>
          : null}>
        {estat === 'fet' && (
          <div>
            <span style={retolCamp}>{t('model_wizard.grading_system')}</span>
            <div><b>{model.size_system_nom || model.size_system_codi}</b></div>
            <div style={{ marginTop: 8 }}>
              <span style={retolCamp}>{t('resum_wizard.run_and_base')}</span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                {(model.size_run_model || '').split('·').filter(Boolean).map(l => (
                  <Xip key={l} marcat={l === model.base_size_label} disabled>
                    {l}{l === model.base_size_label ? ` · ${t('resum_wizard.base')}` : ''}
                  </Xip>
                ))}
              </div>
            </div>
          </div>
        )}
      </FilaDefinicio>
    )
  }

  return (
    <Subespai num={3} titol={t('resum_wizard.step_sizes')} estat="ara">
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
          <Boto variant="ter" onClick={onCancel}>{t('model_wizard.cancel')}</Boto>
          <Boto variant="pri" onClick={desar} disabled={desant || !valid}>
            {desant ? t('model_wizard.saving') : t('resum_wizard.save_sizes')}
          </Boto>
        </div>
      </div>
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
function PasGraduacio({ model, estat, onObrir, desa, onCancel }) {
  const { t } = useTranslation()
  const obert = estat === 'ara'
  const grsId = model?.grading_rule_set ?? null
  const [joc, setJoc] = useState(null)
  const [jocs, setJocs] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [sel, setSel] = useState(grsId)
  const [desant, setDesant] = useState(false)
  const { executa, dialeg } = useConfirmacioRuleset()

  // El joc VIGENT, per poder-lo pintar amb el pas tancat (les eleccions fixades i visibles de §8f).
  useEffect(() => {
    if (!grsId) { setJoc(null); return undefined }
    let viu = true
    gradingRuleSets.get(grsId).then(r => { if (viu) setJoc(r.data || null) }).catch(() => {})
    return () => { viu = false }
  }, [grsId])

  // El CATÀLEG només es carrega quan el subespai s'obre: amb el pas tancat no hi ha res a triar i
  // dues crides per cada fitxa de model serien dues crides per res. En obrir, la tria parteix
  // SEMPRE del que el model té desat — la mateixa llei que el pas 2 (§419).
  useEffect(() => {
    if (!obert) return undefined
    let viu = true
    setSel(grsId)
    Promise.all([
      // `amb_regles: 1` com al wizard: un joc sense regles no és una opció llunyana, és un
      // bloqueig dur al backend (400 `ruleset_buit`). Oferir-lo seria oferir un carreró sense
      // sortida, que no és el que «no amagar» vol dir.
      gradingRuleSets.list({ page_size: 200, amb_regles: 1 }),
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
  }, [obert, grsId])

  // Els eixos del MODEL, tal com els porta el seu detall. El `fit` va en MAJÚSCULES perquè
  // `Model.fit_type` és un choice ('Regular') i els jocs el declaren pel codi del vocabulari
  // ('REGULAR'): sense normalitzar, un joc que declara el fit no casaria mai amb cap model.
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
    // Les confirmacions (joc d'un altre client · esborrat de residents) les porta el hook
    // compartit, que reintenta amb UN flag per cas. Aquí no se'n reimplementa cap.
    await desa({ grading_rule_set_id: sel }, 'resum_wizard.grading_saved',
      p => executa(flags => models.updateStep2(model.id, { ...p, ...flags })))
    setDesant(false)
  }

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
          <div>
            <span style={retolCamp}>{t('dependency.ruleset')}</span>
            <div><b>{joc?.nom || model.grading_rule_set_nom || model.grading_rule_set}</b></div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
              {(joc?.targets_codis || []).map(c => (
                <Xip key={c} marcat disabled>{t(`model_wizard.target_${c}`, c)}</Xip>
              ))}
              {joc?.construction_codi && <Xip marcat disabled>{t(`model_wizard.construction_${joc.construction_codi}`, joc.construction_codi)}</Xip>}
              {joc?.fit_type_codi && <Xip marcat disabled>{t(`model_wizard.fit_${joc.fit_type_codi}`, joc.fit_type_codi)}</Xip>}
            </div>
            <div style={{ marginTop: 8, color: 'var(--text-soft)' }}>
              {t('model_sheet.grading_rules_label')}: {joc?.regles_count ?? 0}
            </div>
          </div>
        )}
      </FilaDefinicio>
    )
  }

  return (
    <Subespai num={4} titol={t('resum_wizard.step_grading')} estat="ara">
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
          <Boto variant="ter" onClick={onCancel}>{t('model_wizard.cancel')}</Boto>
          {/* EL SEU DESAR ÉS L'ÚNIC BLAU d'aquesta columna (§8f). Re-desar el joc que ja hi és no
              és una acció: el backend no en faria res (`canvia_joc` mira que el joc sigui UN
              ALTRE) i el botó no ha de prometre una feina que no passarà. */}
          <Boto variant="pri" onClick={desar} disabled={desant || !sel || sel === grsId}>
            {desant ? t('model_wizard.saving') : t('resum_wizard.save_grading')}
          </Boto>
        </div>
      </div>
      {dialeg}
    </Subespai>
  )
}
