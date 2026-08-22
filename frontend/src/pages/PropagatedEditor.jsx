import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { IconAlertTriangle } from '@tabler/icons-react'
import client from '../api/client'
import { models, presaEscalat } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import PecesDelModel from '../components/model/PecesDelModel'
import SubTabs from '../components/ui/SubTabs'
import { SENSE_PRESA, TANCADA, estatDeLaPresa } from '../utils/estatPresa'
import CheckMeasureEditor from '../components/model/CheckMeasureEditor'
import { fittingSource } from '../components/model/measureSources'
import { filesDeLaPeca } from '../utils/identitatMesura'
import { buildEscalatGroups, buildEscalatRows, escalatRuleLeadCols } from '../components/model/fittingGridAdapter'
import { mesuraSemblaIncrement } from '../utils/plausibilitatMesura'
import { formatLen } from '../utils/format'
import { useUnit } from './fittingShared'

// ESCALAT — la taula del model per talles, sobre l'editor únic MeasureGrid.
//
// ⚠️ E1/B3 (17/08) — AQUESTA PANTALLA HA CANVIAT DE NATURALESA. El que hi havia escrit aquí
// deia: «editar una cel·la PROPAGA per regla a les germanes (endpoint escalat/ajustar-talla →
// propaga_ancoratges)». Era cert i era el defecte: la columna «Fit actual» EDITAVA LA CORBA
// TEÒRICA —escrivia `BaseMeasurement`/`ModelGradingOverride` i re-derivava els specs a cada
// tecla—, de manera que «Mesurar prenda» clonava com a teòric el número que el tècnic acabava
// d'anotar i la desviació sortia sempre zero (DIAGNOSI_E1 §3.2).
//
// ARA ÉS EL PAS 1 DEL FLUX E1: la PRESA de les peces físiques arribades. «Fit actual» anota a
// `PieceFittingLine.valor_real` (porta `fitting/model/<id>/presa/`) i NO toca res del domini.
// E2a (QA d'Agus, 17/08) — per talla es veuen DOS valors: **Mesura** (la teòrica de contracte)
// i **Fit actual** (l'arribada). Hi havia una tercera columna, «Propagada», i ensenyava el
// MATEIX número que la teòrica mentre no s'hagués propagat —o sigui quasi sempre—: dues
// columnes amb la mateixa xifra fan buscar la diferència que no hi és.
// El vermell segueix dient que la peça arribada s'aparta del que s'esperava (R1), i el seu
// referent segueix sent la teòrica (v. `cellaEscalat`).
//
// Decidir (acceptar/ajustar/rebutjar) NO es fa aquí: és el pas 2, «Mesurar prenda», i NOMÉS a
// la talla base (R2, guard partit d'E1/B1). Propagar segueix sent l'acte conscient de Mesures.
// El règim per POM es canvia amb setPomRegim; la corba vigent surt de taula-mesures.
export default function PropagatedEditor({ modelId, onClose, inline = false, readOnly = false }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reloadKey, setReloadKey] = useState(0)   // remunta MeasureGrid en canvi de règim (re-sembra)
  const [presa, setPresa] = useState(null)        // E1/B3 — estat de la presa viva + valors
  // ── E2c (QA d'Agus, 17/08) · LA DECISIÓ ENTRA AQUÍ DINS ──────────────────────────────────
  // La barra R5 NAVEGAVA a `?tab=Mesures&fitting_session=<id>`, i el tècnic havia de sortir del
  // tab per decidir a la talla base i tornar-hi per veure'n l'efecte. Ara el mateix component
  // de decisió es MUNTA aquí com a secció pròpia: la barra obre i tanca en comptes de portar.
  //
  // 🔑 NO ÉS UN COMPONENT NOU NI UN CONTRACTE PARAL·LEL (v. la diagnosi E2, Bloc 1): és el
  // MATEIX `CheckMeasureEditor` amb la MATEIXA font `fittingSource` i les mateixes portes de
  // servidor. L'única cosa que aquesta pantalla ha d'aportar de nou és el RELLOTGE: la tasca
  // `size_check`, que fins ara obria `ModelSheet` en aterrar-hi.
  // E2c-bis/C1 — SUB-TAB, no panell plegable. La decisió és una SECCIÓ GERMANA de la presa
  // dins de la mateixa pantalla (NORMA §8b-bis), i el commutador és el mateix component que
  // fa servir el tab Mesures (`ui/SubTabs`), no un de nou.
  // ── ESCALAT/VIGENT (21/08, ordre d'Agus) · LA CORBA DEL MODEL TÉ VISTA PRÒPIA ───────────
  // La pestanya prometia «consulta de l'escalat vigent» i obria la PRESA. I la presa no és la
  // corba: les seves teòriques són un CLON congelat de la `GradingVersion` que hi havia quan es
  // va obrir (`cellaEscalat`: `teorica = presa.teoric ?? vigent`), o sigui que amb una presa de
  // la v6 viva la columna «Mesura» ensenyava la v6 mentre el model ja anava per la v9. El teòric
  // vigent només es veia creant una presa NOVA — un gest que escriu al domini per poder mirar.
  //
  // Ara són tres vistes germanes i la primera és la que la pestanya prometia.
  const [vista, setVista] = useState('vigent')        // 'vigent' | 'presa' | 'decisio'
  const [decisioTaskId, setDecisioTaskId] = useState(null)
  // 🔑 ...PERÒ NO QUAN S'HI VE A MESURAR. «Mesurar set» (E3b) resol la sessió i la peça des de
  // `ModelSheet` i tot seguit posa `editing='Escalat'`, que arriba aquí com a `readOnly:false`.
  // Aterrar-hi al «Vigent» —taula de consulta, sense on anotar— repetiria exactament el defecte
  // que això arregla, amb els papers canviats: el gest diu «mesurar» i la pantalla obre una
  // consulta. Consulta → «Vigent»; gest d'escriptura → «Presa».
  // Sortir del mode edició NO torça la vista: qui hagi anat a parar on sigui s'hi queda.
  useEffect(() => { if (!readOnly) setVista('presa') }, [readOnly])

  // E1/B3 — DUES fonts, i cadascuna diu una cosa que l'altra no sap:
  //   · `taula-mesures` → la CORBA VIGENT del model (teòrica propagada);
  //   · `fitting/model/<id>/presa/` → la PRESA de les peces arribades (+ l'estat de la presa).
  // La segona no bloqueja la primera: si falla o no hi ha presa oberta, la graella surt com
  // sempre i el rètol d'estat ho diu. Buidar la taula perquè no hi ha presa seria el pitjor
  // error d'una superfície de feina.
  const load = useCallback(() => {
    setLoading(true)
    return Promise.all([
      client.get(`/api/v1/models/${modelId}/taula-mesures/`)
        .then(res => { setData(res.data); return true })
        .catch(() => { setErr(t('model_measurements.propagated_load_err')); return false }),
      presaEscalat.get(modelId).then(r => setPresa(r.data)).catch(() => setPresa(null)),
    ]).finally(() => setLoading(false))
    // E3b — `readOnly` HI ENTRA I ÉS LOAD-BEARING. «Mesurar set» crea la sessió i la peça DES DE
    // FORA (`ModelSheet`) i tot seguit posa `editing='Escalat'`, que és el que arriba aquí com a
    // `readOnly:false`. Sense això aquest component es quedaria amb l'estat de presa que va
    // llegir en muntar-se —«no n'hi ha cap»— i la graella seguiria de lectura just després del
    // gest que l'havia d'obrir: el botó funcionaria i no ho semblaria.
  }, [modelId, readOnly, t])

  useEffect(() => { load() }, [load])
  // Identitat de model per al contenidor de peça (dependència, joc de regles i run).
  useEffect(() => { models.get(modelId).then(r => setModelInfo(r.data)).catch(() => {}) }, [modelId])

  // E2c-bis — l'estat de la presa, pel MATEIX punt únic que feia servir la barra retirada.
  // El badge del sub-tab és `pendents_base` (les bases que queden per decidir); amb dues
  // prendes n'hi ha dues, i `estatDeLaPresa` ja ho resol.
  const estatPresa = estatDeLaPresa(presa)
  const diaDeLaPresa = estatPresa.session?.data
    ? new Date(estatPresa.session.data).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' })
    : null
  // E3a — LA GRAELLA NOMÉS ACCEPTA UNA TECLA SI LA PRESA ÉS VIVA, i el predicat és el de
  // `estatDeLaPresa`, que deriva del MATEIX `presa_oberta` que el guard del servidor. Amb això
  // els 409 per cel·la deixen d'existir PER CONSTRUCCIÓ i no per un missatge més amable: a la QA
  // de les 20:54 se'n van teclejar tres seguits sobre una presa que s'acabava de segellar.
  // Els DOS estats sense presa hi entren —tancada i cap—; enumerar-los aquí seria la segona llei.
  const potEscriure = !readOnly && estatPresa.escrivible
  const esActa = estatPresa.estat === TANCADA

  // FIX-A/PAS-5 — DE QUINA GRADUACIÓ PARLA AQUESTA PRESA.
  //
  // Les teòriques d'una presa són un CLON dels `GradedSpec` de la versió que hi havia quan es va
  // crear (`create_piece_fitting`). Propagar en crea una de NOVA i la presa es queda penjant de
  // la vella: al banc 1383 hi conviuen les dues —una peça a la v2 i una altra a la v6—, i fins
  // avui la pantalla les pintava idèntiques. Qui mirava la graella comparava mesures reals
  // contra una corba que ja no era la del model, sense res que ho digués.
  //
  // El servidor porta LES DUES versions i la comparació es fa aquí (`escalat_presa_views`): si
  // és un problema o no depèn del que la persona estigui fent, i això no ho pot decidir un
  // endpoint.
  const gvPresa = presa?.grading_version || null
  const gvVigent = presa?.grading_version_vigent || null
  const presaEsRancia = !!(gvPresa && gvVigent && gvPresa.id !== gvVigent.id)

  const base = (data?.base_size || '').trim()
  // Identitat estable: `data?.size_run || []` fabricava un array nou a cada render i feia recalcular
  // els useMemo de sota sempre (i el linter ho canta).
  const sizes = useMemo(() => data?.size_run || [], [data])
  const gridGroups = buildEscalatGroups(sizes, base, t)
  // ── TRAM E · LA PORTA DEL VALOR VERMELL, DES D'AQUESTA PANTALLA ──────────────────────────
  // La cel·la prestada (regla STEP sense valor per a la talla) s'edita a la columna «Mesura»,
  // que és on la xifra prestada VIU. El que s'hi escriu és el valor de la REGLA
  // (`valors_step`), no una presa ni un override: sobreviu a les re-propagacions perquè és la
  // regla, i per això el gest té porta pròpia i no reaprofita la de la columna del costat.
  //
  // El backend hi re-propaga in place, o sigui que en tornar cal rellegir: la fila perd el
  // vermell i la corba de les talles de més enfora es mou amb ella (és el que vol dir STEP).
  const desaValorRegla = useCallback((row, talla, valor) => (
    models.setStepValor(modelId, row.pom_id, {
      talla, valor, capa: row.capa, instancia: row.instancia, garment: row.garment,
    }).then(() => load())
  ), [modelId, load])

  const gridRows = useMemo(
    () => buildEscalatRows(data?.rows || [], sizes, base, presa?.preses || {},
                           { onDesaValorRegla: readOnly ? null : desaValorRegla }),
    [data, sizes, base, presa, readOnly, desaValorRegla])

  // ── LES FILES DEL «VIGENT»: LES MATEIXES, SENSE PRESA ────────────────────────────────────
  // `preses = {}` és tota la diferència, i és la que fa que la columna digui el vigent: sense
  // presa, `cellaEscalat` cau a `vigent` (que és el que `taula-mesures` serveix des de la
  // `GradingVersion` vigent). Cap font nova, cap crida nova — la dada JA hi era, sense vista.
  //
  // ⚠️ LA PORTA DEL VALOR VERMELL NO HI ENTRA (`onDesaValorRegla: null`). Aquí també hi ha
  // cel·les prestades (regla STEP sense valor per a la talla) i es pinten igual de vermelles,
  // però aquesta vista és CONSULTA: el gest d'escriure el valor a la regla viu a la Presa, que
  // és on el tècnic hi és per treballar. Una escriptura al domini no es cola en una vista de
  // consulta perquè el component la sabia fer.
  const gridRowsVigent = useMemo(
    () => buildEscalatRows(data?.rows || [], sizes, base, {}, {}),
    [data, sizes, base])
  const gridGroupsVigent = useMemo(
    () => buildEscalatGroups(sizes, base, t, { nomesVigent: true }), [sizes, base, t])
  // LA VERSIÓ DE LA CORBA, del mateix payload que la pinta (`taula-mesures` l'emet des de T4).
  // No es llegeix de la presa: el «Vigent» ha de saber dir de quina versió parla ENCARA QUE no
  // hi hagi hagut mai cap presa, que és justament el cas en què la pantalla no deia res.
  const gvNum = data?.grading_version_number ?? null
  const gvDia = data?.grading_version_data
    ? new Date(data.grading_version_data).toLocaleDateString('ca-ES',
        { day: '2-digit', month: '2-digit' })
    : null

  // Índex per lineId → {vigent, base} de la fila. El fan servir les dues guardes de sota, i és
  // l'única lectura de l'estat que necessiten (cap dada nova del backend).
  const perLinia = useMemo(() => {
    const m = new Map()
    for (const r of gridRows) {
      for (const s of sizes) {
        const a = r.cells?.[s]?.active
        // C4/BLOC 3 — hi entra el `pom_id` (i els eixos) perquè l'escriptura no hagi de
        // desmuntar el lineId: la fila ja sap qui és, i el mapa ja la té localitzada.
        // E2b — `fantasma` viatja amb la línia perquè la GUARDA-RAIL de sota el pugui
        // distingir: amb el pre-omplert, `value` ÉS la teòrica i la guarda es menjaria la
        // confirmació sense dir res.
        if (a) m.set(a.lineId, { vigent: a.value, base: r.base_value_cm, codi: r.codi, talla: s,
                                 fantasma: !!a.fantasma,
                                 pom_id: r.pom_id, capa: r.capa, instancia: r.instancia,
                                 garment: r.garment })
      }
    }
    return m
  }, [gridRows, sizes])

  // E2c — OBRIR EL PANELL ÉS OBRIR LA FEINA, i per tant el rellotge. `open-task` és el mateix
  // servei que fa servir `ModelSheet` per aterrar a «Mesurar prenda» (crea-si-falta + assigna +
  // En curs), amb la sessió al davant perquè lligui la tasca a AQUESTA presa. Es fa un sol cop:
  // tancar i reobrir el panell no encunya cap tasca nova.
  //
  // Sense sessió no s'obre res, i és la mateixa llei que el botó ③ de `ModelSheet`: val més no
  // entrar que entrar a una superfície que se li assembla. La barra ja deixa el botó inert amb
  // la presa BUIDA; això és el cinturó.
  const triaVista = useCallback((k) => {
    if (k !== 'decisio') { setVista(k); return }
    const sid = presa?.session?.id
    if (!sid) { setErr(t('escalat.sense_presa_oberta')); return }
    setVista('decisio')
    // E3a — SOBRE UNA ACTA NO S'OBRE CAP RELLOTGE. La decisió d'una presa tancada ja està
    // presa: consultar-la no és feina i encunyar-hi una tasca `size_check` faria comptar temps
    // de treball a qui només mira enrere —i deixaria una tasca oberta que després algú hauria
    // de tancar. El panell es munta igual, en lectura.
    if (esActa) return
    if (decisioTaskId != null) return
    models.openTask(modelId, 'size_check', sid)
      .then(r => setDecisioTaskId(r.data.task_id))
      // El panell ja és obert i la decisió es pot prendre igualment: el que es perd si això
      // falla és el compta-temps, no la feina. Dir-ho i no tancar-li la porta a sobre.
      .catch(() => setErr(t('escalat.decisio_sense_rellotge')))
  }, [decisioTaskId, presa, modelId, esActa, t])

  // La pregunta de plausibilitat viva: {lineId, valor, base, codi, talla, resolt}. Mai un bloqueig.
  const [confirmPlaus, setConfirmPlaus] = useState(null)
  const confirmRef = useRef(null)

  // L'escriptura de debò, un cop passades les guardes.
  const desa = useCallback((lineId, value) => {
    // C4/BLOC 3 — el POM i la talla surten del `perLinia`, NO de trossejar el lineId. La
    // primera meitat del lineId ha passat a ser la clau sencera de la mesura
    // (`{pom}|{capa}|{inst}`), i el `Number(...)` que hi havia n'hauria tret `NaN`: la crida
    // se n'aniria a `/escalat/NaN/ajustar-talla/` i cada cel·la de l'Escalat deixaria de desar.
    // Llegir-ho del mapa, a més, treu del mig la pregunta de com es desmunta una clau: la fila
    // ja porta els camps per separat, que és el que `pom/identitat.py` demana que es faci.
    const info = perLinia.get(lineId)
    if (!info) return Promise.resolve()
    // 🔑 E1/B3 — AQUESTA CEL·LA JA NO EDITA LA CORBA: ANOTA UNA PRESA.
    //
    // Això cridava `models.escalatAjustarTalla`, que escrivia `BaseMeasurement` (o un
    // `ModelGradingOverride`) i re-derivava els specs a cada tecla. Per això «Mesurar prenda»
    // clonava com a teòric el número que el tècnic acabava d'anotar i la desviació sortia
    // sempre zero: el pas 1 destruïa el referent del pas 2 (DIAGNOSI_E1 §3.2).
    //
    // Ara va a `PieceFittingLine.valor_real` per una porta que no toca el domini. El que la
    // presa NO fa —consolidar, propagar— continua tenint les seves portes, i cadascuna és un
    // acte que algú decideix.
    return presaEscalat.desa(modelId, info.pom_id, info.talla, value,
                             { capa: info.capa, instancia: info.instancia,
                               garment: info.garment })
      .then(res => { load(); return res })
      .catch(e => {
        // Els dos rebutjos que aquesta porta pot donar tenen CARA: sense presa oberta no hi
        // ha on anotar (i el gest d'obrir-la és a la barra d'estat), i una sessió segellada és
        // acta. Un rebuig mut faria que el tècnic seguís mesurant creient que es desa.
        const codi = e?.response?.data?.codi
        if (codi === 'sense_presa_oberta' || codi === 'sessio_segellada') {
          setErr(t(`escalat.${codi}`))
        }
        throw e   // MeasureGrid ha de saber igualment que la cel·la NO s'ha desat.
      })
  }, [modelId, perLinia, load, t])

  // Anotació de la presa d'una cel·la. Retorna l'axios promise; la resposta porta la cel·la
  // resolta pel servidor (teòric · real · desviació · estat) i `load()` refresca la graella.
  const onGridSave = useCallback((lineId, value) => {
    if (value == null) return Promise.resolve()
    const info = perLinia.get(lineId)

    // GUARDA-RAIL — reescriure el valor que la cel·la JA té és un NO-OP: ni crida. `info.vigent`
    // és ara LA PRESA que hi ha desada (no la corba), o sigui que això estalvia una escriptura
    // idèntica, no una re-derivació: el motiu ha canviat amb la naturalesa de la cel·la, però
    // la crida que no es fa segueix sent la que no es pot equivocar mai.
    //
    // 🚨 E2b — I NO S'APLICA AL FANTASMA. Amb el pre-omplert, `info.vigent` ÉS la teòrica que
    // la cel·la ensenya sense que ningú l'hagi mesurada: confirmar-la és un GEST (ha de crear
    // la presa i escriure `presa_at`), i aquesta guarda l'hauria engolit en silenci —el número
    // coincideix— deixant l'usuari convençut que havia confirmat. La guarda existeix per
    // estalviar escriptures IDÈNTIQUES a una presa que ja hi és; sense presa no hi ha res a
    // estalviar.
    if (info && !info.fantasma && info.vigent !== '' && info.vigent != null
        && Number(info.vigent) === Number(value)) {
      return Promise.resolve()
    }

    // FIX-4 — GUARDA DE PLAUSIBILITAT, en DESAR (mai en teclejar: interrompre a cada tecla faria
    // impossible escriure «1» abans de «16»). Pregunta, no bloqueja: el «sí» desa amb normalitat.
    if (info && mesuraSemblaIncrement(value, info.base)) {
      return new Promise((resolve, reject) => {
        confirmRef.current = { resolve, reject }
        setConfirmPlaus({ lineId, valor: value, base: info.base, codi: info.codi, talla: info.talla })
      })
    }

    return desa(lineId, value)
  }, [perLinia, desa])

  // «Desar igualment» → l'escriptura normal. Cancel·lar → cap escriptura i la cel·la torna al seu
  // valor desat (remuntatge de la graella): que no quedi a la pantalla un número que no és a la BD.
  const resolPlaus = useCallback((desaIgualment) => {
    const pend = confirmPlaus
    const cb = confirmRef.current
    confirmRef.current = null
    setConfirmPlaus(null)
    if (!pend || !cb) return
    if (!desaIgualment) {
      cb.resolve(null)
      load().then(() => setReloadKey(k => k + 1))
      return
    }
    desa(pend.lineId, pend.valor).then(cb.resolve, cb.reject)
  }, [confirmPlaus, desa, load])

  // ⚠️ E1/B3 — AQUÍ HI HAVIA EL RÈTOL DE «VERSIÓ SEGELLADA» I EL BOTÓ DE SUPERAR-LA, i se'n
  // van perquè han quedat INASSOLIBLES, no per gust. El 409 `sealed` el donava el motor en
  // re-derivar els specs, i aquesta pantalla el disparava perquè cada tecla els re-derivava.
  // Ara la cel·la anota una presa i no toca cap `GradingVersion`: el segell no s'hi pot
  // trobar mai, i un rètol que no pot sortir és pitjor que no tenir-ne —qui llegeixi el
  // fitxer en dedueix que l'Escalat escriu al grading, que és precisament el que ja no fa.
  //
  // EL GEST NO ES PERD i no calia que visqués aquí: la porta que SÍ topa amb el segell és
  // «Propagar a grading» (`ModelSheet.onPropagarClick`), que ja ofereix la doble confirmació
  // amb `allow_reopen_sealed`. Superar un segell és un acte de propagació, no de presa.

  // Canvi de règim del POM (endpoint independent de la sessió) → rellegeix i remunta la graella.
  // S42/F1 · Q1-bis — LA REGLA ÉS DE LA PEÇA. `ModelGradingRule` és única per
  // `(model, pom, garment)` des de T3 i `set_pom_regim_view` ja resol l'eix des del #12d;
  // aquesta crida l'identificava amb el `pom_id` pelat, o sigui que canviar el règim des del
  // contenidor de la 02 reescrivia la regla de la MARE. La fila el porta (`taula-mesures`
  // l'emet), com a l'ajust de talla d'aquí sobre.
  const onRegimChange = (row, nova) => {
    if (!nova || nova === (row.logica ?? '')) return
    models.setPomRegim(modelId, row.pom_id, nova, row.garment || '')
      .then(() => load().then(() => setReloadKey(k => k + 1)))
      .catch(() => setErr(t('model_measurements.regim_err')))
  }

  const unit = useUnit()
  const leadCols = escalatRuleLeadCols(t, onRegimChange, readOnly, unit, sizes)
  // Les MATEIXES columnes de regla, en lectura: al «Vigent» la regla és el que EXPLICA la corba
  // (la frase d'intervals de F4-quater al costat dels números que produeix), no una cosa que
  // s'hi editi. El règim s'edita a la Presa i a Mesures, que és on el tècnic hi va a treballar.
  const leadColsVigent = escalatRuleLeadCols(t, onRegimChange, true, unit, sizes)

  // inline=true: incrustat com a contingut de pestanya (sense overlay fix ni botó tancar).
  const outerStyle = inline
    ? {}
    : { position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(0,0,0,0.45)', display: 'flex', flexDirection: 'column' }
  const bodyStyle = inline
    ? { background: 'var(--white)' }
    : { flex: 1, overflow: 'auto', background: 'var(--white)', padding: '1rem' }

  return (
    <div style={outerStyle}>
      <div style={bodyStyle}>
        {/* Overlay (ruta /escalat o modal "Veure escalat"): botó tancar sempre disponible. */}
        {!inline && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
            <button type="button" onClick={onClose}
              style={{ padding: '6px 16px', border: '0.5px solid var(--border)', borderRadius: 6,
                       background: 'var(--white)', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              {t('model_measurements.propagated_close')}
            </button>
          </div>
        )}
        {/* SET-2/T7-A3 · MATEIX PATRÓ QUE MESURES: la barra crema de resum del model se'n va
            (el que deia ja és a la capçalera de la pàgina, i el run i la base baixen al
            contenidor de peça, dits amb tipografia). La FRANJA CONTEXTUAL no era part del
            resum i es queda: és l'únic lloc que diu de què va aquesta pantalla. */}
        <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap',
                      padding: '0 2px 10px', fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
          <span>
            <strong>{t('model_sheet.tab_grading')}</strong>
            {' — '}
            {readOnly ? t('model_measurements.propagated_hint_ro') : t('model_measurements.propagated_hint')}
          </span>
        </div>
        {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{err}</div>}
        {/* ── E2c-bis/C1+C4 · SUB-TABS, I LA BARRA D'ESTAT FORA ─────────────────────────────
            La barra deia «4 de 90» · «Talles: M·S» · «18 per decidir». Tot això o bé el diu la
            taula (quines talles tenen presa es veu mirant-la) o bé el diu ara el BADGE del
            sub-tab, que és l'únic número que fa prendre una decisió: quantes bases queden per
            decidir. Un rètol que repeteix el que hi ha a sota no informa: ocupa.

            🚩 PROPOSTA DE POSICIÓ (decisió visual final d'Agus, C4): l'ancoratge de la presa
            —«Presa del 16/08»— va a la DRETA de la fila de sub-tabs i no dins del sub-tab de
            Decisió. El motiu és el flux asíncron que E1 persegueix: al taller es mesura i al
            despatx es decideix, potser un altre dia, i qui obre la pantalla ha de saber DE QUINA
            presa parla **mentre mesura**, no només quan decideix. Dins del sub-tab de Decisió
            quedaria amagat justament a la meitat del flux que més el necessita.

            🚨 E3a — EL RACÓ JA NO ÉS UN GEST EN CAP ESTAT, i això és el que arregla el camí que
            la QA de les 20:54 va destapar (§D2 de la diagnosi). Aquí hi havia un botó que
            NAVEGAVA a `?tab=Mesures`, i com que `models/:id/escalat` i `models/:id` munten el
            MATEIX `ModelSheet`, React Router reconcilia en comptes de remuntar: `editing` sobrevivia
            valent `'Escalat'` i el SALT DE SUPERFÍCIE (`ModelSheet:664-675`) llegia el canvi de tab
            com un canvi d'EINA → obria la tasca `pom` i aterrava a Definició POM. Un botó que diu
            «obrir la presa» i acaba definint POMs.
            El gest de crear/entrar viu ara al botó PRINCIPAL «Mesurar set» (E3b), que no navega:
            resol la sessió i la peça allà mateix. Aquest racó torna a ser el que sempre havia
            hagut de ser —«DE QUINA PRESA PARLEM»— i per tant una ETIQUETA, en els tres estats. */}
        <SubTabs
          items={[
            // PRIMERA i per defecte: és el que la pestanya promet des de sempre.
            { key: 'vigent', label: 'escalat.subtab_vigent', icon: 'ti-chart-grid-dots' },
            { key: 'presa', label: 'escalat.subtab_presa', icon: 'ti-ruler-measure' },
            // El badge és feina PENDENT, i sobre una acta no en queda cap: pintar-hi «1 per
            // decidir» sobre una presa tancada seria demanar una decisió que ja no es pot prendre.
            { key: 'decisio', label: 'escalat.subtab_decisio', icon: 'ti-checkbox',
              badge: esActa ? null : estatPresa.pendents_base },
          ]}
          actiu={vista} onTria={triaVista}
          /* EL RACÓ DE LA DRETA DIU DE QUINA COSA PARLEM, i les tres vistes no parlen de la
             mateixa: al «Vigent», de la VERSIÓ de la corba; a la Presa i a la Decisió, de la
             presa —i allà no es toca ni un píxel (llei E1: la foto no es re-deriva mai, i el
             seu banner de versió és part de la foto). */
          dreta={vista === 'vigent' ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6,
                           fontFamily: 'IBM Plex Mono, monospace',
                           fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}
                  title={gvNum != null
                    ? t('escalat.vigent_versio_nota', { num: gvNum, data: gvDia || '—' })
                    : undefined}>
              {gvNum != null
                ? t('escalat.vigent_versio', { num: gvNum })
                : t('escalat.vigent_sense')}
            </span>
          ) : (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6,
                           fontFamily: 'IBM Plex Mono, monospace',
                           fontSize: 'var(--fs-caption)',
                           color: esActa ? 'var(--text-muted)' : 'var(--text-soft)' }}
                  title={esActa ? t('escalat.presa_tancada_nota') : undefined}>
              {estatPresa.estat === SENSE_PRESA
                ? t('escalat.presa_cap')
                : t(esActa ? 'escalat.presa_tancada_del' : 'escalat.presa_del',
                    { data: diaDeLaPresa || '—' })}
              {/* FIX-A/PAS-5 — LA VERSIÓ, I L'AVÍS QUAN NO ÉS LA VIGENT.
                  La versió es diu SEMPRE que se sap: saber de quina corba parla la presa és part
                  de saber de quina presa parles, i amagar-la mentre tot va bé vol dir que el dia
                  que aparegui ningú no en sabrà el significat. El que apareix només quan cal és
                  l'AVÍS —fons i tinta d'alerta—, perquè és el que demana una decisió.
                  Tokens de la casa (llei G8): mai cap hex. */}
              {gvPresa && (
                <span
                  style={presaEsRancia
                    ? { padding: '1px 6px', borderRadius: 4,
                        background: 'var(--warn-state-bg)', color: 'var(--warn-ink)',
                        border: '1px solid var(--warn-state)', fontWeight: 600 }
                    : { color: 'var(--text-muted)' }}
                  title={presaEsRancia
                    ? t('escalat.presa_versio_rancia_nota',
                        { presa: gvPresa.num, vigent: gvVigent.num })
                    : t('escalat.presa_versio_nota', { num: gvPresa.num })}>
                  {presaEsRancia && <i className="ti ti-alert-triangle" aria-hidden="true"
                                       style={{ fontSize: 12, marginRight: 3,
                                                verticalAlign: '-1px' }} />}
                  {t('escalat.presa_versio', { num: gvPresa.num })}
                </span>
              )}
            </span>
          )} />
        {/* L'avís, escrit. El badge de dalt marca ON és el problema; això diu QUÈ vol dir i què
            se'n pot fer, que en un racó de 60px no hi cap. Va aquí i no en un toast: no és un
            esdeveniment, és un ESTAT de la pantalla i ha de durar el que duri. */}
        {presaEsRancia && vista !== 'vigent' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8,
                        padding: '8px 12px', borderRadius: 6,
                        border: '1px solid var(--warn-state)',
                        background: 'var(--warn-state-bg)', color: 'var(--warn-ink)',
                        fontSize: 'var(--fs-body)' }}>
            <IconAlertTriangle size={18} stroke={1.5} style={{ flexShrink: 0 }} />
            <span>{t('escalat.presa_versio_rancia', { presa: gvPresa.num,
                                                      vigent: gvVigent.num })}</span>
          </div>
        )}
        {/* FIX-4 — la pregunta de plausibilitat. MAI un bloqueig dur: hi ha peces petites
            legítimes, i una validació que impedeix desar només ensenya a esquivar-la. Es
            pregunta, i el «sí» desa amb normalitat. */}
        {confirmPlaus && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                        marginBottom: 8, padding: '10px 12px', borderRadius: 6,
                        border: '1px solid var(--warn)', background: 'var(--warn-bg)' }}>
            <IconAlertTriangle size={18} stroke={1.5} style={{ color: 'var(--warn)', flexShrink: 0 }} />
            <span style={{ fontSize: 'var(--fs-body)', flex: 1, minWidth: 260 }}>
              {t('model_measurements.plaus_mesura', {
                valor: formatLen(confirmPlaus.valor, unit),
                base: formatLen(confirmPlaus.base, unit),
              })}
            </span>
            <button type="button" onClick={() => resolPlaus(true)}
              style={{ padding: '6px 14px', borderRadius: 6, border: '0.5px solid var(--border)',
                       background: 'var(--white)', cursor: 'pointer',
                       fontSize: 'var(--fs-body)', whiteSpace: 'nowrap' }}>
              {t('model_measurements.plaus_desa')}
            </button>
            <button type="button" onClick={() => resolPlaus(false)}
              style={{ padding: '6px 10px', borderRadius: 6, border: 0, background: 'transparent',
                       cursor: 'pointer', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
              {t('common.cancel')}
            </button>
          </div>
        )}
        {/* SET-2/T7-B2b — un contenidor per prenda; v. `PecesDelModel`. */}
        {/* SET-2/T7-B8 — cada contenidor, les seves files (v. `CheckMeasureEditor`). El desat
            d'Escalat també va per LÍNIA amb la PK. */}
        {/* E2c-bis/C1 — LA TAULA DE PRESA ÉS EL SUB-TAB «Presa». Les dues seccions són
            germanes i se'n veu UNA: tenir-les totes dues alhora era el panell desplegable que
            aquesta peça substitueix, i deixava la decisió a mitja pàgina de distància. */}
        {/* ── LA VISTA «VIGENT»: LA CORBA DEL MODEL, I RES MÉS ────────────────────────────
            Mateix `PecesDelModel` + mateix `MeasureGrid` que la Presa —la taula d'una pantalla
            no ha de canviar de forma segons què s'hi miri—, amb tres diferències i totes tres
            volgudes: files sense presa (la columna diu el VIGENT), grups `nomesVigent` (sense
            la columna «Fit actual», que aquí no tindria on anotar) i `editable={false}`.

            No hi ha cap gest: consultar la corba no crea res. És exactament el que faltava —
            fins avui, veure el teòric vigent obligava a obrir una presa NOVA, o sigui a escriure
            al domini per poder mirar. */}
        {vista === 'vigent' && (
        <PecesDelModel model={modelInfo}>{peca => {
        const filesVigent = filesDeLaPeca(gridRowsVigent, peca ? (peca.codi || '') : null)
        return (<>
        {loading && !data ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
        ) : filesVigent.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('model_measurements.propagated_empty')}</div>
        ) : (
          <MeasureGrid
            key={`vigent:${modelId}:${reloadKey}`}
            editable={false}
            rows={filesVigent} groups={gridGroupsVigent}
            leadCols={leadColsVigent}
            leadGroupLabel={t('measuregrid.grup_regla')}
            groupsLabel={t('measuregrid.grup_mesures')}
          />
        )}
        </>)
        }}</PecesDelModel>
        )}

        {vista === 'presa' && (
        <PecesDelModel model={modelInfo}>{peca => {
        const filesDelContenidor = filesDeLaPeca(gridRows, peca ? (peca.codi || '') : null)
        return (<>
        {loading && !data ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
        ) : filesDelContenidor.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('model_measurements.propagated_empty')}</div>
        ) : (
          <MeasureGrid
            key={`${modelId}:${reloadKey}`}
            editable={potEscriure}
            rows={filesDelContenidor} groups={gridGroups}
            leadCols={leadCols}
            leadGroupLabel={t('measuregrid.grup_regla')}
            groupsLabel={t('measuregrid.grup_mesures')}
            onSave={onGridSave}
          />
        )}
        </>)
        }}</PecesDelModel>
        )}

        {/* ── E2c · EL PANELL DE DECISIÓ, DINS D'ESCALAT ──────────────────────────────────
            La talla base es decideix aquí mateix: el tècnic acaba d'anotar les peces arribades
            i decideix sense canviar de tab ni perdre de vista la taula que acaba d'omplir.

            És el MATEIX component que el tab Mesures (`CheckMeasureEditor` + `fittingSource`),
            amb els MATEIXOS props que li passa `ModelSheet`. `lockRules` hi va per la mateixa
            raó que allà: en una sessió, el règim i els deltes són lectura —s'hi decideixen
            preses, no s'hi edita el patrimoni del model.

            LA SESSIÓ VA PRIMA (`{id}` i prou) i n'hi ha prou: `resolvePieceFitting` només llegeix
            `fittingSession.id`, i si no té la peça a mà la crea o la recupera amb el 409
            `piece_exists`. No cal rellegir la sessió sencera per muntar-lo.

            En tancar el panell (o en gravar la sessió) es rellegeix la presa: decidir a la base
            i propagar mou la corba, i la taula de sobre ha de dir la veritat sense recarregar. */}
        {/* E3a — SOBRE UNA ACTA, CONSULTA. La sessió tancada ja té `session.id` (E3a/B1), o sigui
            que el panell es munta igual i ensenya el que es va decidir; el que canvia és que hi
            entra en lectura i sense rellotge. Abans això ni s'arribava a muntar —el payload no
            portava sessió— i el sub-tab semblava avariat. */}
        {vista === 'decisio' && presa?.session?.id && (
          <section style={{ marginTop: 16 }}>
            {esActa && (
              <div style={{ marginBottom: 10, fontSize: 'var(--fs-caption)',
                            color: 'var(--text-muted)' }}>
                {t('escalat.decisio_tancada_nota')}
              </div>
            )}
            <CheckMeasureEditor
              embedded
              model={modelInfo || { id: modelId }}
              readOnly={readOnly || esActa}
              taskId={decisioTaskId}
              source={fittingSource}
              sourceCtx={{ fittingSession: presa.session }}
              lockRules
              onFeedback={fb => { if (fb?.type === 'err') setErr(fb.text) }}
              onResolved={() => { setVista('presa'); load() }}
              onSessionSaved={() => { setVista('presa'); load() }} />
          </section>
        )}
      </div>
    </div>
  )
}
