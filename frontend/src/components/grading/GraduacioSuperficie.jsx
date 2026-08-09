import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import client from '../../api/client'
import { models } from '../../api/endpoints'
import { etiquetaCapa, etiquetaInstancia } from '../../utils/capaInstancia'
import { useEstatDiccionari } from '../../utils/diccionariMesuresFont'
import { useElements } from '../../utils/vocabulariDominiFont'
import { InfoTraduccio, AMPLADES } from '../EditableTable/EditableTable'

// LA GRADUACIÓ ÉS UNA SUPERFÍCIE PRÒPIA (P0.5d · Agus, 06/08, a pantalla).
//
// No és la taula de Gravar POM amb quatre columnes més. Triar joc al contenidor (P0.5a) no porta
// a Definició POM: porta AQUÍ. I aquí ja no es toquen mesures — el valor de talla base hi és en
// LECTURA, perquè graduar és decidir com creix una mesura, no quina és.
//
// …PERÒ EN COLUMNA PRÒPIA, no enganxat al nom (Agus, 06/08). Aquesta pantalla és de la MATEIXA
// FAMÍLIA que Definició POM i la consulta (v8.1): mateixes versaletes, mateixa densitat, mateix
// carril de valor amb `--sel` acotat pels dos costats i la talla en cos gran a la capçalera.
// Amb el valor dins la cel·la del nom les xifres no formaven columna i es perdia la lectura
// VERTICAL de les mesures, que és com es mira una taula d'aquestes. El que es clona és
// l'estructura, no s'inventa un aire nou: `EditableTable` és la referència.
//
// ── QUÈ HI HA A CADA FILA, I QUÈ SE'N DESA ──────────────────────────────────────────────────
// La fila que el joc resol es pinta PLENA; la que ningú resol es pinta «—» i és editable des de
// zero (aquí viu l'ENTRADA MANUAL). Editar-ne una i l'altra acaben al MATEIX lloc —la regla
// resident del model— per la MATEIXA porta que ja existia: `set_pom_regim_view`
// (`POST /models/<id>/pom/<pom_id>/regim/`, upsert amb actualització selectiva per presència de
// camp). No s'hi ha creat cap circuit d'escriptura nou; el que faltava era la pantalla.
//
// ── 🔴 LA LLIÇÓ DEL 31/07, QUE AQUEST FITXER NO POT TORNAR A TRENCAR ─────────────────────────
// «Gravar Graduació» envia NOMÉS les files que l'usuari ha tocat. MAI sembra LINEAR per defecte
// a les no tocades.
//
// El mecanisme és `edicions`: un Map que neix BUIT i on només hi entra el que un gest humà ha
// canviat, camp a camp. El que es desa és literalment el contingut del Map — no es deriva mai
// del que la taula pinta. Aquesta és la diferència exacta amb el bug del model 1302: allà el
// payload es construïa recorrent les FILES (i una fila pintada amb la regla d'un altre es
// materialitzava sola); aquí es construeix recorrent les EDICIONS, i una fila que ningú ha
// tocat no té entrada al Map i per tant no genera cap crida.
//
// ⚠️ EL QUE AQUESTA PANTALLA NO POT PROMETRE, i convé saber-ho llegint-la: que després de
// gravar només hi hagi tantes regles residents com files tocades. Assignar un joc ja en
// materialitza una per regla del joc (`update-step2` → `materialize_model_grading_rules`,
// wipe-and-recreate), i això passa ABANS que aquesta pantalla existeixi per a l'usuari. El que
// SÍ que promet, i és el que la llei demana, és que aquesta pantalla no n'afegeix ni en toca cap
// que l'usuari no hagi tocat: es comprova amb `origen`, no amb un recompte.
//
// ── LA REGLA ÉS DEL POM, NO DE LA FILA ──────────────────────────────────────────────────────
// `ModelGradingRule` no porta capa ni instància (decisió de domini amb acta: mateix POM, mateix
// increment a totes les capes i instàncies). Les germanes hi surten com a files —amb el seu nom
// compost, que és com se les reconeix— però COMPARTEIXEN regla: editar-ne una les mou totes, i
// se n'envia UNA sola crida per `pom_id`. El gest d'instància (píndoles, ＋) NO viu aquí.
const FS_HEAD = '9.5px'
const FS_VAL = '12.5px'
// Tipografia de la v8.1, la mateixa família que `EditableTable` (v. la nota d'allà: cap graó
// `--fs-*` cau sobre 9,5/12,5 px). Els COLORS segueixen sent tokens, sempre.
const thS = {
  padding: '4px 10px', textAlign: 'left', fontSize: FS_HEAD,
  fontWeight: 500, whiteSpace: 'nowrap',
  textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)',
  borderBottom: '1px solid var(--border)',
}
const tdS = { padding: '4px 10px', verticalAlign: 'middle', fontSize: FS_VAL }

// Q2 (06/08) — LES AMPLADES SÓN LES DE LA CONSULTA, IMPORTADES. Aquí hi havia `W_NOM = 236`
// copiat a mà «perquè la recerca el trobés als dos llocs», i la resta de columnes amb números
// propis (110/90/100/100 contra 96/84/96/96). Copiar no és compartir: es va bifurcar el mateix
// dia. Ara venen d'`EditableTable.AMPLADES`, que és l'única declaració.

const btnPrimary = (disabled) => ({
  background: disabled ? 'var(--bg-muted)' : 'var(--accio)',
  color: disabled ? 'var(--text-muted)' : 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 18px',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)',
  border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}

// ELS RÈGIMS OFERTS A L'AUTORIA ELS DIU L'ENDPOINT, no aquesta pantalla. La regla és exactament
// la que hi havia escrita aquí —ZERO i EXCEPTION no s'ofereixen com a tria nova— però ara ve amb
// la dada: `/vocabulari/` marca cada règim amb `autorable` (coda F2.2). Aquell comentari era
// l'ÚNICA raó escrita a tot el projecte per no oferir-los, i vivia en un fitxer de pantalla; ara
// viu al costat de la dada i `SizeMapSetup` —que oferia ZERO sense cap raó— hi queda alineat.
//
// EL QUE NO CANVIA: si una fila ja porta un règim no autorable, es manté a la SEVA llista perquè
// el valor real no s'emmascari. Poder-lo llegir i poder-lo triar no són la mateixa pregunta.
// Valors de DADA: no es tradueixen.

// Els deltes només volen dir alguna cosa sota LINEAR. Sota FIXED/ZERO la mesura no creix, i sota
// STEP el creixement viu a `valors_step` (una llista per talla que aquesta pantalla no edita).
const acceptaDeltes = (logica) => logica === 'LINEAR' || !logica

const buit = (v) => v === null || v === undefined || v === ''

// Mirall EXACTE de `es_linear_degenerada` (backend `pom/grading_regime.py`): LINEAR amb delta 0 i
// sense trencament no gradua res i el backend el rebutja amb 400 LINEAR_INCREMENT_ZERO. Es mira
// aquí perquè la persona ho vegi a la fila i no en un toast després d'haver premut Gravar.
function esLinearDegenerada(r) {
  if (r.logica !== 'LINEAR') return false
  const teBreak = !buit(r.talla_break_label)
    || (!buit(r.increment_break) && Number(r.increment_break) !== 0)
  if (teBreak) return false
  return buit(r.increment_base) || Number(r.increment_base) === 0
}

/** Text lliure → número o null. Accepta la coma decimal, que és com s'escriu aquí. */
function num(v) {
  if (buit(v)) return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

export default function GraduacioSuperficie({ model, onTancar, onObrirContenidor, onGravat }) {
  const { t, i18n } = useTranslation()
  // Les capes surten del diccionari de la BD (F2.2), no de cap llista escrita aquí.
  const { dicc } = useEstatDiccionari()
  // Els règims que un tècnic pot TRIAR: els que l'endpoint marca `autorable`. Sense vocabulari
  // la llista va buida i el select d'una fila només ofereix el règim que la fila ja porta —que
  // és el que toca dir quan no sabem quins són oferibles.
  const { elements: vocRegims } = useElements('regims_graduacio')
  const regimsAutorables = useMemo(
    () => (vocRegims || []).filter(r => r.autorable).map(r => r.codi), [vocRegims])
  const lang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  const modelId = model?.id
  const [data, setData] = useState(null)
  const [carregant, setCarregant] = useState(true)
  const [err, setErr] = useState('')
  const [gravant, setGravant] = useState(false)
  const [feedback, setFeedback] = useState(null)   // {type:'ok'|'err', text}
  // 🔴 EL MAP DE LA LLEI. Neix buit i només hi entra el que un gest humà canvia.
  // Map<pom_id, {logica?, increment_base?, increment_break?, talla_break_label?}>
  const [edicions, setEdicions] = useState(new Map())

  const carrega = useCallback(() => {
    if (!modelId) return
    setCarregant(true)
    client.get(`/api/v1/models/${modelId}/taula-mesures/`)
      .then(res => { setData(res.data); setErr('') })
      .catch(() => setErr(t('graduacio.superficie.load_err')))
      .finally(() => setCarregant(false))
  }, [modelId, t])

  useEffect(() => { carrega() }, [carrega])

  const files = useMemo(() => data?.rows ?? [], [data])
  const sizeRun = useMemo(() => data?.size_run ?? [], [data])

  // El valor VIGENT d'un camp: l'edició si n'hi ha (encara que sigui null: esborrar és una
  // decisió), i si no, el que va arribar del servidor.
  const valor = useCallback((row, camp) => {
    const ed = edicions.get(row.pom_id)
    if (ed && camp in ed) return ed[camp]
    return row[camp]
  }, [edicions])

  // La regla VIGENT d'una fila (servidor + edicions a sobre), que és la que es valida i es desa.
  const reglaDe = useCallback((row) => ({
    logica: valor(row, 'logica'),
    increment_base: valor(row, 'increment_base'),
    increment_break: valor(row, 'increment_break'),
    talla_break_label: valor(row, 'talla_break_label'),
  }), [valor])

  const canvia = useCallback((row, camp, v) => {
    setFeedback(null)
    setEdicions(prev => {
      const next = new Map(prev)
      const cur = { ...(next.get(row.pom_id) || {}) }
      cur[camp] = v
      // Escriure un delta sobre una fila que no té CAP regla vol dir LINEAR, i val més que la
      // pantalla ho digui que no pas que el backend ho decideixi en silenci: el desplegable
      // passa a LINEAR a la vista i entra a l'edició com un canvi explícit i visible, que la
      // persona pot canviar tot seguit. (Això NO és sembrar: la fila l'acaba de tocar algú.)
      if (camp !== 'logica' && !row.logica && !('logica' in cur) && !buit(v)) cur.logica = 'LINEAR'
      next.set(row.pom_id, cur)
      return next
    })
  }, [])

  // Les files que l'usuari ha tocat, i les que a més queden en LINEAR degenerada (que el backend
  // rebutjaria). Es compten per POM, que és la unitat de la regla.
  const pomsTocats = useMemo(() => [...edicions.keys()], [edicions])
  const degenerades = useMemo(() => {
    const out = new Set()
    files.forEach(r => {
      if (!edicions.has(r.pom_id)) return
      if (esLinearDegenerada(reglaDe(r))) out.add(r.pom_id)
    })
    return out
  }, [files, edicions, reglaDe])

  // 🔴 EL PAYLOAD SURT DE `edicions`, NO DE `files`. Una crida per POM tocat, i dins de cada
  // crida NOMÉS els camps que s'han canviat: `set_pom_regim_view` actualitza per presència de
  // clau, o sigui que el que no s'envia no es toca.
  const grava = useCallback(async () => {
    if (!pomsTocats.length || gravant) return
    if (degenerades.size) {
      setFeedback({ type: 'err', text: t('graduacio.superficie.err_linear_zero') })
      return
    }
    setGravant(true)
    setFeedback(null)
    const fallits = []
    for (const pomId of pomsTocats) {
      const camps = edicions.get(pomId) || {}
      const payload = {}
      if ('logica' in camps) payload.logica = camps.logica || null
      if ('increment_base' in camps) payload.increment_base = num(camps.increment_base)
      if ('increment_break' in camps) payload.increment_break = num(camps.increment_break)
      if ('talla_break_label' in camps) payload.talla_break_label = camps.talla_break_label || null
      if (!Object.keys(payload).length) continue
      try {
        await models.setPomRule(modelId, pomId, payload)
      } catch (e) {
        const fila = files.find(r => r.pom_id === pomId)
        fallits.push(`${fila?.pom_code || pomId}: ${e?.response?.data?.detail || t('graduacio.superficie.err_generic')}`)
      }
    }
    setGravant(false)
    if (fallits.length) {
      setFeedback({ type: 'err', text: fallits.join(' · ') })
      return
    }
    setEdicions(new Map())
    setFeedback({ type: 'ok', text: t('graduacio.superficie.gravat', { count: pomsTocats.length }) })
    carrega()
    onGravat?.()
  }, [pomsTocats, gravant, degenerades, edicions, modelId, files, t, carrega, onGravat])

  // ── Cel·les ────────────────────────────────────────────────────────────────────────────────
  const inputStyle = (ko) => ({
    width: '100%', boxSizing: 'border-box', textAlign: 'right',
    border: `0.5px solid ${ko ? 'var(--danger, #b3261e)' : 'var(--border)'}`,
    borderRadius: 4, padding: '2px 6px', fontSize: FS_VAL, font: 'inherit',
    fontVariantNumeric: 'tabular-nums', background: 'var(--white)', color: 'var(--text-main)',
  })

  const nomDe = (row) => row.nom_canonic_model
    || row.client_name_en || row.nom_en || row.nom_ca || row.pom_code || ''

  const cos = () => files.map((row, i) => {
    const n = i + 1
    const regla = reglaDe(row)
    const tocat = edicions.has(row.pom_id)
    const ko = degenerades.has(row.pom_id)
    const inst = etiquetaInstancia(row.instancia)
    // Mateixa regla que la consulta: la traducció només surt si NO repeteix el nom visible.
    const nomVisible = nomDe(row)
    const candidat = row.nom_traduit_model || row.nom_ca || ''
    const traduit = candidat && candidat !== nomVisible ? candidat : ''
    const deltes = acceptaDeltes(regla.logica)
    // D'ON VE EL QUE ES VEU. Això ho decidia `regla_origen` tot sol, i mentia: la regla del
    // JOC (`pom.GradingRule`) no té camp `origen`, o sigui que quan el model gradua de debò pel
    // joc arribava `null` i aquí es llegia «no és MANUAL... doncs del model». Just al revés.
    //
    // Ara mana `regla_es_resident`, que diu de quina TAULA ha sortit la regla, i `origen` només
    // desempata dins de les residents:
    //   · no resident        → del JOC en directe (el model no té cap regla pròpia)
    //   · resident + MANUAL  → del MODEL (algú l'ha escrita, aquí o a Gravar POM)
    //   · resident + la resta→ del JOC (còpia materialitzada en assignar-lo)
    const delJoc = !!regla.logica
      && (row.regla_es_resident === false || (row.regla_es_resident && row.regla_origen !== 'MANUAL'))
    const regims = regimsAutorables.includes(row.logica) || !row.logica
      ? regimsAutorables : [...regimsAutorables, row.logica]
    return (
      <tr key={row.id} style={{ background: tocat ? 'var(--fila-activa)' : 'transparent' }}>
        {/* # — el número de fila, com a la consulta (mateix to i cos). */}
        <td style={{ ...tdS, color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>{n}</td>
        <td style={{ ...tdS, color: 'var(--text-muted)' }}>{etiquetaCapa(row.capa || 'exterior', dicc, lang)}</td>
        {/* EL CODI EN `--gold` I L'ESTRELLA DELS KEY, com a la consulta: el codi és el que el
            tècnic busca amb l'ull, i el ☆ diu quines mesures manen sense llegir-ne cap. */}
        <td style={{ ...tdS, whiteSpace: 'nowrap', color: 'var(--gold)' }}>
          {row.nom_fitxa || row.client_code || row.pom_code || ''}
          {row.is_key && (
            <i className="ti ti-star" title="KEY"
              style={{ fontSize: 9, marginLeft: 5, color: 'var(--gold)', verticalAlign: 'middle' }} />
          )}
        </td>
        {/* EL NOM EMBOLICA, com a la consulta: mateix `whiteSpace:'normal'` dins d'una columna
            de la mateixa amplada (`W_NOM`). Anava en una sola línia, i era d'aquí que sortia
            l'única diferència d'alçada de fila entre les dues taules —14px— quan padding, cossos
            i capçalera ja eren idèntics: no era densitat, era que aquí el nom no embolicava. */}
        <td style={tdS}>
          <div style={{ fontSize: FS_VAL, color: 'var(--text-main)', whiteSpace: 'normal' }}>
            {nomDe(row)}
            {inst && <span style={{ fontWeight: 500 }}>{` · ${inst}`}</span>}
            {/* LA ⓘ DE LA TRADUCCIÓ — el MATEIX component de la consulta (exportat, no copiat).
                Només quan diu una cosa diferent del nom visible: repetir-lo no és informació. */}
            {traduit && <InfoTraduccio text={traduit} />}
          </div>
        </td>
        {/* EL VALOR DE TALLA BASE, COLUMNA PRÒPIA — el mateix carril que la consulta (`--sel`
            acotat pels dos costats), en LECTURA: aquí no es canvien mesures, es decideix com
            creixen. Anava enganxat al nom amb un `marginLeft`, i així les xifres no formaven
            columna: no es podien llegir en vertical, que és com es mira una taula de mesures. */}
        <td style={{ ...tdS, textAlign: 'right', background: 'var(--gold-pale)',
                     borderLeft: '1px solid var(--border)', borderRight: '1px solid var(--border)',
                     fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
          {row.base_value_cm === null || row.base_value_cm === undefined
            ? <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>—</span>
            : row.base_value_cm}
        </td>
        {/* Procedència: què mira la persona quan es pregunta «d'on surt això». */}
        <td style={{ ...tdS, fontSize: FS_HEAD, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          {!regla.logica ? '' : delJoc ? t('graduacio.superficie.origen_joc') : t('graduacio.superficie.origen_model')}
        </td>
        <td style={tdS}>
          {/* El desplegable de règim ha de CABRE a l'amplada de la família (`AMPLADES.regim`):
              amb l'encoixinat de l'input hi demanava 4px de més i la columna es desquadrava de
              la consulta. El que es retalla és l'aire dels costats, no el text. */}
          <select value={regla.logica || ''} onChange={e => canvia(row, 'logica', e.target.value || null)}
            style={{ ...inputStyle(ko), padding: '2px 2px', textAlign: 'left', cursor: 'pointer' }}>
            <option value="">—</option>
            {regims.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </td>
        <td style={tdS}>
          {/* Q2 — `size={4}`: un `<input>` amb `width:100%` conserva l'amplada INTRÍNSECA del
              seu `size` per defecte (20 caràcters), i en una taula d'amplada de contingut és
              aquesta la que mana: la columna del delta demanava 202px per a un «1.5», el doble
              que a la consulta. Amb `size` curt, la columna la decideix el `minWidth` de la
              capçalera, que és el de la família. */}
          <input type="text" inputMode="decimal" size={4} disabled={!deltes}
            value={buit(regla.increment_base) ? '' : regla.increment_base}
            onChange={e => canvia(row, 'increment_base', e.target.value)}
            title={deltes ? '' : t('graduacio.superficie.delta_na', { regim: regla.logica })}
            style={{ ...inputStyle(ko), opacity: deltes ? 1 : 0.4 }} />
        </td>
        <td style={tdS}>
          {/* Q2 — `size={4}`: un `<input>` amb `width:100%` conserva l'amplada INTRÍNSECA del
              seu `size` per defecte (20 caràcters), i en una taula d'amplada de contingut és
              aquesta la que mana: la columna del delta demanava 202px per a un «1.5», el doble
              que a la consulta. Amb `size` curt, la columna la decideix el `minWidth` de la
              capçalera, que és el de la família. */}
          <input type="text" inputMode="decimal" size={4} disabled={!deltes}
            value={buit(regla.increment_break) ? '' : regla.increment_break}
            onChange={e => canvia(row, 'increment_break', e.target.value)}
            title={deltes ? '' : t('graduacio.superficie.delta_na', { regim: regla.logica })}
            style={{ ...inputStyle(ko), opacity: deltes ? 1 : 0.4 }} />
        </td>
        <td style={tdS}>
          <select value={regla.talla_break_label || ''} disabled={!deltes}
            onChange={e => canvia(row, 'talla_break_label', e.target.value || null)}
            style={{ ...inputStyle(ko), textAlign: 'left', cursor: deltes ? 'pointer' : 'default',
                     opacity: deltes ? 1 : 0.4 }}>
            <option value="">—</option>
            {sizeRun.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </td>
      </tr>
    )
  })

  // ── Capçalera de context ───────────────────────────────────────────────────────────────────
  const joc = model?.grading_rule_set_nom || model?.grading_rule_set_detall?.nom || null
  const dada = (etiqueta, v) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontSize: FS_HEAD, textTransform: 'uppercase', letterSpacing: '0.05em',
                     color: 'var(--text-muted)' }}>{etiqueta}</span>
      <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
        {v || <span style={{ color: 'var(--text-muted)' }}>—</span>}
      </span>
    </div>
  )

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20,
        flexWrap: 'wrap', border: '0.5px solid var(--border)', borderRadius: 8,
        background: 'var(--bg-muted)', padding: '12px 16px', marginBottom: 14,
      }}>
        <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {dada(t('graduacio.superficie.model'), model?.codi_intern)}
          {dada(t('graduacio.superficie.joc'), joc || t('graduacio.superficie.sense_joc'))}
          {dada(t('graduacio.superficie.talla_base'), data?.base_size)}
          {dada(t('graduacio.superficie.run'), sizeRun.join(' · '))}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" onClick={onObrirContenidor} style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
            <i className="ti ti-adjustments" style={{ fontSize: 14 }} aria-hidden="true" />
            {' '}{joc ? t('graduacio.superficie.canviar_joc') : t('graduacio.superficie.triar_joc')}
          </button>
          <button type="button" onClick={onTancar} style={btnSecondary}>
            <i className="ti ti-arrow-left" style={{ fontSize: 14 }} aria-hidden="true" />
            {' '}{t('graduacio.superficie.tornar')}
          </button>
        </div>
      </div>

      {err && <p style={{ color: 'var(--danger, #b3261e)', fontSize: 'var(--fs-body)' }}>{err}</p>}
      {carregant && <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('app.loading')}</p>}

      {!carregant && !err && (
        <>
          <div style={{ overflowX: 'auto', border: '0.5px solid var(--border)', borderRadius: 8 }}>
            {/* Q2 — LA TAULA NO VA AL 100%. Anava-hi, i com que totes les columnes menys `#`
                tenien amplada fixada, el sobrant de la pantalla se n'anava sencer a la primera:
                el forat entre `#` i CAPA de la captura de les 13:04. La consulta no ha fet mai
                això —taula d'amplada de contingut dins d'un `overflowX:auto`— i aquesta és la
                mateixa taula. Clonat literal d'`EditableTable`. */}
            <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
              <thead>
                <tr>
                  {/* ORDRE DE LA FAMÍLIA (Agus, 06/08): # · CAPA · POM · NOM · TALLA BASE ·
                      VE DE · RÈGIM · Δ · Δ BREAK · TALLA BREAK. El valor va enganxat a la
                      identitat i les regles tanquen la fila. */}
                  {/* El `#` NO porta amplada, com a la consulta: s'encongeix al seu contingut. */}
                  <th style={thS}>#</th>
                  {/* El bloc d'IDENTITAT amb les amplades de la consulta (`width` + `minWidth`,
                      com hi van allà): és el que fa que el nom embolica al mateix punt i que les
                      dues taules tinguin la mateixa alçada de fila. */}
                  <th style={{ ...thS, width: AMPLADES.capa, minWidth: AMPLADES.capa }}>{t('capa.col')}</th>
                  <th style={{ ...thS, width: AMPLADES.codi, minWidth: AMPLADES.codi }}>{t('measuregrid.col_pom')}</th>
                  <th style={{ ...thS, width: AMPLADES.nom, minWidth: AMPLADES.nom }}>{t('measuregrid.col_nom')}</th>
                  {/* v8.1 `th.baseh` — CLONAT de la consulta, no reinventat: l'etiqueta petita
                      nomena la columna i la talla va en cos gran, que és el que la fa trobar
                      sense llegir. Sense talla base declarada es queda el literal de sempre;
                      inventar-hi una «Talla base» prometria una talla que ningú ha dit. */}
                  <th style={{ ...thS, minWidth: AMPLADES.base, textAlign: 'right', background: 'var(--gold-pale)',
                               borderLeft: '1px solid var(--border)', borderRight: '1px solid var(--border)' }}>
                    {data?.base_size ? (
                      <>
                        <span style={{ display: 'block', fontWeight: 600, color: 'var(--gold)' }}>
                          {t('editable_table.col.base_size_label')}
                        </span>
                        <span style={{ display: 'block', fontSize: 15, fontWeight: 600, lineHeight: 1.1,
                                       letterSpacing: 'normal', textTransform: 'none', color: 'var(--text-main)' }}>
                          {data.base_size}
                        </span>
                      </>
                    ) : t('editable_table.col.base_value')}
                  </th>
                  {/* «VE DE» és columna PRÒPIA d'aquesta pantalla (la consulta no la té): no hi ha
                      cap amplada de la família a clonar-hi, i per això declara la seva. */}
                  <th style={{ ...thS, minWidth: 90 }}>{t('graduacio.superficie.col_origen')}</th>
                  {/* Les QUATRE de la regla, amb les amplades de la consulta. Aquí són editables i
                      allà de lectura, però la columna ha de caure al mateix lloc: és la mateixa
                      taula mirada de dues maneres. */}
                  <th style={{ ...thS, minWidth: AMPLADES.regim, borderLeft: '1px solid var(--border)' }}>{t('fitting.grid.regime')}</th>
                  <th style={{ ...thS, minWidth: AMPLADES.delta, textAlign: 'right' }}>{t('editable_table.col.delta')}</th>
                  <th style={{ ...thS, minWidth: AMPLADES.delta_break, textAlign: 'right' }}>{t('editable_table.col.delta_break')}</th>
                  <th style={{ ...thS, minWidth: AMPLADES.talla_break }}>{t('editable_table.col.talla_break')}</th>
                </tr>
              </thead>
              <tbody>
                {files.length === 0
                  ? <tr><td colSpan={10} style={{ ...tdS, color: 'var(--text-muted)', padding: '16px 10px' }}>
                      {t('graduacio.superficie.buit')}
                    </td></tr>
                  : cos()}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        gap: 12, marginTop: 14, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'var(--fs-body)', color: feedback?.type === 'err' ? 'var(--danger, #b3261e)' : 'var(--text-muted)' }}>
              {feedback?.text || (pomsTocats.length
                ? t('graduacio.superficie.tocades', { count: pomsTocats.length })
                : t('graduacio.superficie.res_tocat'))}
            </span>
            <button type="button" onClick={grava} disabled={!pomsTocats.length || gravant}
              style={btnPrimary(!pomsTocats.length || gravant)}>
              {gravant ? t('common.saving') : t('graduacio.superficie.gravar')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
