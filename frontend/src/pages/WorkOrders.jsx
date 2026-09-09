import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { commerce, customers as customersApi } from '../api/endpoints'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import SubTabs from '../components/ui/SubTabs'
import Modal from '../components/ui/Modal'
import { botoPri } from '../components/ui/buttons'
import { EstatBadge, ClassificacioBadge, useCodisEstat } from '../components/commercial/estats'
import {
  Comptador, FilaIdentitat, EstatBuit, Paginacio, camp, forceBarra,
} from '../components/llista/ChromLlista'

// ENCÀRRECS / ORDRES DE TREBALL (`WorkOrder`) — LLISTA CANÒNICA (NORMA_LAYOUT §8b + §8e).
//
// Contenidors d'execució: ORDER (encàrrec d'un model × línia de comanda) i COLLECTOR (col·lector
// mensual per client). **No es creen aquí** —ORDER neix del wizard B4b, COLLECTOR d'un hook
// lazy—, o sigui que aquesta pantalla és de CONSULTA i no té acció primària (§8c): el seu menú
// porta només la fletxa.
//
// **EL TIPUS DEIXA DE SER UN SEMÀFOR.** `kind` anava amb `ORDER` en VERD i `COLLECTOR` en TARONJA:
// un encàrrec d'un model no és «correcte» ni un col·lector mensual és un «avís». És una
// CLASSIFICACIÓ, i les classificacions van neutres (v. `components/commercial/estats`, decisió 3).
//
// Les tres llistes de codis (`KINDS`, `STATUSES`, i el mapa de tipus) se'n van a `/vocabulari/`
// (`tipus_encarrec`, `estats_encarrec`).
//
// LOT 09/09 · LA LLEI DEL NOM ARRIBA AQUÍ. La llista identificava l'encàrrec pel CODI del model
// dins d'una columna «Model/Període» que barrejava dues dades («una columna, dues dades»). Ara el
// NOM del model és la segona columna i la COL·LECCIÓ la tercera, i el codi baixa a secundari sota
// el nom. La columna barrejada se'n va: el període d'un col·lector ocupa la mateixa cel·la del
// nom perquè és el que ANOMENA aquell encàrrec —un col·lector no té model i mai en tindrà—, i
// això no és barrejar dues dades sinó dir el nom de cada mena amb la seva paraula.
// La safata que s'obre en entrar (§8e) i el sentinella de l'absència de filtre.
//
// `ESTAT_PER_DEFECTE` és l'ÚNIC codi de domini escrit en aquest fitxer, i hi és perquè la
// pregunta «quina d'aquestes safates és la feina viva?» no la respon el vocabulari: `/vocabulari/`
// serveix els codis i les etiquetes, no quin d'ells s'obre primer. Serveix per a dues coses —el
// filtre inicial i l'ordre dels tabs— i per això és una constant amb nom i no dos literals solts.
// `TOTES` no és de domini: és una cadena qualsevol que NO sigui buida ni cap codi
// d'`estats_encarrec`, i el que necessita és sobreviure a `setParams`, que esborra els buits.
const ESTAT_PER_DEFECTE = 'OPEN'
const TOTES = 'TOTES'
const PAGE_SIZE = 25
const ORDRE_DEFECTE = { camp: 'number', dir: 'desc' }

const aOrdering = (o) => (o.dir === 'desc' ? `-${o.camp}` : o.camp)

// S'exporten: la fitxa d'encàrrec i la pantalla d'orfes en pinten els mateixos badges.
export function WOStatusBadge({ status, t }) {
  return <EstatBadge clau="estats_encarrec" codi={status}>{t(`workorders.status_${status}`)}</EstatBadge>
}
export function WOKindBadge({ kind, t }) {
  return <ClassificacioBadge>{t(`workorders.kind_${kind}`)}</ClassificacioBadge>
}

export default function WorkOrders() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [total, setTotal] = useState(null)
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  // Selecció múltiple. Viu en memòria i NO a la URL: és una intenció de treball d'aquesta
  // estona, no un estat compartible per enllaç. Es buida en canviar de safata o de cerca,
  // perquè arrossegar una tria a través d'un conjunt que ja no es veu és com es tanca el que
  // no es volia tancar.
  const [triats, setTriats] = useState(() => new Set())
  const [tancant, setTancant] = useState(false)      // diàleg de confirmació obert
  const [enviant, setEnviant] = useState(false)      // guard anti-doble-clic del lot
  const [previ, setPrevi] = useState(null)           // recompte de la passada SECA

  const { codis: estats } = useCodisEstat('estats_encarrec')
  const { codis: tipus } = useCodisEstat('tipus_encarrec')

  const [sp, setSp] = useSearchParams()
  const kindF = sp.get('kind') || ''
  // §8e — «els elements ACABATS no es llisten per defecte (embruten la cerca)». La safata que
  // s'obre en entrar és la feina VIVA; els tancats es demanen. Un encàrrec tancat ja no admet
  // cap gest d'aquesta pantalla —ni tancar-lo, ni triar-lo per al lot— i el seu lloc és a
  // l'historial, no a la primera lectura.
  //
  // 🔑 «Totes» necessita un valor EXPLÍCIT (`TOTES`) i no la cadena buida: `setParams` esborra
  // els paràmetres buits (v. més avall), o sigui que triar «Totes» amb `''` hauria esborrat el
  // paràmetre i tornat al defecte. La safata s'hauria negat a obrir-se i no hauria fallat res.
  const statusF = sp.get('status') || ESTAT_PER_DEFECTE
  const customerF = sp.get('customer') || ''
  // La cerca SÍ que va a la URL: un resultat de cerca es comparteix i es torna a obrir.
  const searchF = sp.get('search') || ''
  const page = Math.max(1, parseInt(sp.get('page') || '1', 10))
  const ordre = useMemo(() => {
    const raw = sp.get('ordering')
    if (!raw) return ORDRE_DEFECTE
    const desc = raw.startsWith('-')
    return { camp: desc ? raw.slice(1) : raw, dir: desc ? 'desc' : 'asc' }
  }, [sp])

  const setParams = useCallback((patch) => {
    // 🔑 QUALSEVOL canvi de consulta BUIDA LA TRIA —safata, cerca, filtre i també pàgina—, i es
    // fa AQUÍ i no en un efecte: la tria d'abans ja no és a la pantalla, i arrossegar-la a
    // través d'un conjunt que l'usuari no té davant és com es tanca el que no es volia tancar.
    // El gest ho ha de dir, no un efecte que ho endreci després.
    setTriats(new Set())
    setSp(prev => {
      const next = new URLSearchParams(prev)
      Object.entries(patch).forEach(([k, v]) => {
        if (v === undefined || v === null || v === '') next.delete(k)
        else next.set(k, v)
      })
      return next
    }, { replace: true })
  }, [setSp])

  const ordenar = useCallback((c) => {
    const dir = (ordre.camp === c && ordre.dir === 'desc') ? 'asc' : 'desc'
    setParams({ ordering: aOrdering({ camp: c, dir }), page: undefined })
  }, [ordre, setParams])

  const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])

  const load = useCallback(() => {
    setLoading(true); setError(false)
    commerce.workOrders.list({
      ...(kindF ? { kind: kindF } : {}),
      // `TOTES` és absència de filtre, no un estat: no viatja al backend.
      ...(statusF && statusF !== TOTES ? { status: statusF } : {}),
      ...(customerF ? { customer: customerF } : {}),
      ...(searchF ? { search: searchF } : {}),
      ordering: aOrdering(ordre), page, page_size: PAGE_SIZE,
    })
      .then(res => {
        const d = res.data
        setItems(Array.isArray(d) ? d : (d.results || []))
        setCount(d?.count ?? (Array.isArray(d) ? d.length : 0))
      })
      .catch(() => { setItems([]); setCount(0); setError(true) })
      .finally(() => setLoading(false))
  }, [kindF, statusF, customerF, searchF, ordre, page])

  const carregaTotal = useCallback(() => {
    commerce.workOrders.list({ page_size: 1 }).then(r => setTotal(r.data?.count ?? null)).catch(() => setTotal(null))
  }, [])

  useEffect(() => { carregaTotal() }, [carregaTotal])
  useEffect(() => { const id = setTimeout(load, 150); return () => clearTimeout(id) }, [load])
  useEffect(() => {
    let alive = true
    customersApi.list({ active: true, page_size: 500 }).then(rows)
      .then(cs => { if (alive) setCustomers(cs) })
      .catch(() => { if (alive) setCustomers([]) })
    return () => { alive = false }
  }, [])

  const commuta = useCallback((id) => setTriats(prev => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  }), [])
  // La casella de la capçalera opera NOMÉS sobre la pàgina visible, que és el que l'usuari té
  // davant: «totes» no pot voler dir files que no ha vist mai.
  const totsVisibles = items.length > 0 && items.every(r => triats.has(r.id))
  const commutaTots = useCallback(() => setTriats(prev => {
    const next = new Set(prev)
    if (items.every(r => next.has(r.id))) items.forEach(r => next.delete(r.id))
    else items.forEach(r => next.add(r.id))
    return next
  }), [items])

  // ELS TABS SURTEN DEL VOCABULARI, no d'una llista escrita aquí: `estats_encarrec` és la
  // mateixa font que alimentava el desplegable que substitueixen, i els seus rètols són els
  // `workorders.status_*` que la casa ja té traduïts. L'única cosa que s'hi afegeix és la
  // safata «totes», que no és cap estat del domini sinó l'absència de filtre.
  //
  // L'ORDRE SÍ QUE ES FIXA AQUÍ, i abans no: el `map` prenia l'ordre en què `/vocabulari/`
  // tornés els codis, o sigui que la barra podia dir «Tancats · Oberts» sense que res fallés.
  // Els codis segueixen sent del vocabulari; el que es declara és que la feina VIVA va primer.
  const tabs = useMemo(() => {
    const codis = [...(estats || [])]
    codis.sort((a, b) => (a === ESTAT_PER_DEFECTE ? -1 : b === ESTAT_PER_DEFECTE ? 1 : 0))
    return [
      ...codis.map(codi => ({ key: codi, label: `workorders.status_${codi}` })),
      { key: TOTES, label: 'workorders.tab_all' },
    ]
  }, [estats])

  // ── TANCAR ELS SELECCIONATS ──────────────────────────────────────────────────────────────
  //
  // La confirmació ha de dir DUES coses abans de tocar res: quants encàrrecs es tanquen i que
  // les tasques pendents que hi pengin quedaran DEDUÏDES. La segona és la que no es veu i la
  // que no té marxa enrere; callar-la seria demanar un sí a cegues.
  //
  // El compte és `triats.size` i no una derivada de les files: la tria es buida a cada canvi de
  // consulta, o sigui que el que hi ha triat és sempre el que es veu.
  // 🚨 **UNA PASSADA SECA ABANS DE DEMANAR EL SÍ.**
  //
  // El gest INDIVIDUAL no dedueix mai a la primera: `close(id, {})` va sense `cancel_pending`, el
  // backend respon 409 amb `pending_proposals` i la fitxa ENSENYA quines tasques concretes es
  // deduiran abans que ningú confirmi res. El lot no pot ser més destructiu que el gest que diu
  // replicar: amb `cancel_pending:true` cablejat i una sola confirmació genèrica, marcar la
  // casella de capçalera i prémer volia dir deduir totes les Pending de N encàrrecs sense que en
  // cap moment s'hagués dit quantes — i el número només sortia al toast, quan ja no hi ha marxa
  // enrere.
  //
  // Ara, en obrir el diàleg es fa la MATEIXA crida amb `cancel_pending:false`, que no escriu res
  // (`close_work_order` surt per `if pending and not cancel_pending` sense tocar la BD) i torna
  // el recompte exacte. La confirmació diu tres números MESURATS, no promesos.
  const passadaSeca = useCallback(() => {
    setTancant(true); setPrevi(null)
    commerce.workOrders.closeBulk({ ids: [...triats], cancel_pending: false })
      .then(res => {
        const r = res.data?.resultats || []
        setPrevi({
          tancables: r.filter(x => x.ok || x.motiu === 'pending').length,
          bloquejats: r.filter(x => x.motiu === 'blocked').length,
          deduibles: r.reduce((a, x) => a + (x.pending_proposals?.length || 0), 0),
        })
      })
      // Si la passada seca falla, NO s'endevina: el diàleg ho diu i el botó de confirmar es
      // queda apagat. Confirmar un lot destructiu sense saber-ne l'abast és el que això evita.
      .catch(() => setPrevi({ error: true }))
  }, [triats])

  const tancaSeleccionats = useCallback(() => {
    if (!triats.size || enviant) return
    setEnviant(true)
    commerce.workOrders.closeBulk({ ids: [...triats], cancel_pending: true })
      .then(res => {
        const d = res.data || {}
        const nOk = (d.tancats || []).length
        const nKo = (d.bloquejats || []).length + (d.errors || []).length
        const deduides = (d.resultats || []).reduce((a, r) => a + (r.deduides || 0), 0)
        setTancant(false); setPrevi(null)
        setTriats(new Set())
        // El resum diu els tres números que importen, i el PARCIAL no s'amaga: si algun ha
        // quedat bloquejat, el to és d'avís i no d'èxit. Els motius per encàrrec viuen a la
        // seva fitxa —aquí caben els comptes, no la llista.
        setFeedback({
          type: nKo ? 'warn' : 'ok',
          text: nKo
            ? t('workorders.bulk_close_partial', { ok: nOk, ko: nKo, deduides })
            // `count` i no `ok`: i18next pluralitza sobre `count`, i amb un sol encàrrec la
            // frase deia «1 encàrrecs tancats». El resum PARCIAL no es pluralitza perquè és una
            // línia d'estadística (etiqueta: número) i aquesta forma no demana concordança.
            : t('workorders.bulk_close_ok', { count: nOk, deduides }),
        })
        load(); carregaTotal()
      })
      .catch(err => {
        setTancant(false); setPrevi(null)
        setFeedback({ type: 'err', text: err?.response?.data?.error || t('workorders.bulk_close_error') })
      })
      .finally(() => setEnviant(false))
  }, [triats, enviant, t, load, carregaTotal])

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const cols = useMemo(() => [
    {
      // CONTROL, no dada: va abans del número i no ordena. El `stopPropagation` és obligatori
      // —`TaulaLlista` posa l'`onClick` d'obrir a tot el `<tr>`— o triar una fila navegaria.
      key: 'tria', label: '', min: 40, max: 40, align: 'center',
      // `renderCap` ja el preveu la graella canònica per a aquesta columna exacta (v. el
      // comentari de `Capcalera`): la pantalla hi posa el control de conjunt i el `th` conserva
      // la caixa de la norma.
      renderCap: () => (
        <input type="checkbox" checked={totsVisibles} onChange={commutaTots}
          aria-label={t('workorders.select_all')}
          style={{ cursor: 'pointer', accentColor: 'var(--gold)', width: 14, height: 14 }} />
      ),
      render: r => (
        <input type="checkbox" checked={triats.has(r.id)}
          onClick={e => e.stopPropagation()}
          onChange={() => commuta(r.id)}
          aria-label={t('workorders.select_one', { n: r.number })}
          style={{ cursor: 'pointer', accentColor: 'var(--gold)', width: 14, height: 14 }} />
      ),
    },
    {
      // ── LES SIS COLUMNES (Agus 09/09) ──────────────────────────────────────────────────
      // REF DEL MODEL · NOM · COL·LECCIÓ · TIPUS · CLIENT · ESTAT. I cap més.
      //
      // Se'n van NÚMERO i TASQUES. El número d'encàrrec no és el que algú busca amb la vista
      // escombrant la llista —el busca qui ja el té d'un correu, i per a això hi ha el
      // cercador—, i el comptador de tasques és un detall de dins de l'encàrrec, no un eix de
      // la safata. Cap dels dos desapareix: el número viatja al `title` de cada fila i mana a
      // la fitxa; el recompte és a la fitxa.
      //
      // La REF passa a columna PRÒPIA i surt de la cel·la del nom, on el commit anterior
      // l'havia posada com a secundari. Amb la ref com a columna, repetir-la sota el nom seria
      // dir el mateix dues vegades a la mateixa fila.
      key: 'ref', label: t('workorders.col_ref'), min: 130, max: 170, sort: 'model__codi_intern',
      estil: { color: 'var(--text-soft)' },
      titol: r => r.model_codi || undefined,
      // Un COLLECTOR no té model i mai en tindrà (`collector_no_model_no_orderline`): no té ref
      // i es pinta el guió de la casa, no una cadena inventada.
      render: r => r.model_codi || '—',
    },
    {
      // LA DADA REINA. §8e: porta el pes, i el pes va a la CEL·LA (`td.c-nom{font-weight:600}`),
      // no a un `span` de dins — amb el 600 al fill, el computat del `td` deia 400 i la
      // bidireccional ho marcava. A UNA SOLA LÍNIA amb ellipsis: la §8e prohibeix el salt, que
      // trenca la fila d'una línia i obliga a re-enfocar a cada salt.
      //
      // El COLLECTOR posa aquí el seu període, que és el que l'anomena.
      key: 'nom', label: t('workorders.col_nom'), min: 220, max: 380, sort: 'model__nom_prenda',
      estil: { fontWeight: 600 },
      titol: r => (r.kind === 'COLLECTOR'
        ? t('workorders.collector_period', { period: r.period || '—' })
        : (r.model_nom || t('workorders.no_name'))),
      render: r => (r.kind === 'COLLECTOR'
        ? t('workorders.collector_period', { period: r.period || '—' })
        : (r.model_nom || t('workorders.no_name'))),
    },
    {
      // COL·LECCIÓ. Buida en un col·lector (no té model) i en un model que no en declara: guió
      // de la casa, mai una cadena inventada. Secundària en tinta, com la ref.
      key: 'collection', label: t('workorders.col_collection'), min: 130, max: 200,
      sort: 'model__collection',
      estil: { color: 'var(--text-soft)' },
      titol: r => r.model_collection || undefined,
      render: r => r.model_collection || '—',
    },
    {
      key: 'kind', label: t('workorders.col_kind'), min: 110, max: 140, sort: 'kind',
      render: r => <WOKindBadge kind={r.kind} t={t} />,
    },
    {
      key: 'customer', label: t('workorders.col_customer'), min: 170, max: 280, sort: 'customer',
      titol: r => r.customer_nom || undefined,
      render: r => r.customer_nom || '—',
    },
    {
      key: 'status', label: t('workorders.col_status'), min: 90, max: 120, sort: 'status',
      render: r => <WOStatusBadge status={r.status} t={t} />,
    },
  ], [t, triats, totsVisibles, commuta, commutaTots])

  return (
    <>
      <div style={forceBarra}>
        <PageMenu backTo="/" backTitle={t('workorders.back_title')} />
      </div>

      {/* Àncora de mesura (`qa_auditoria_computats` / bidireccional). No és crom i no pinta res:
          és el SENYAL que diu que aquesta pantalla s'ha muntat de debò. Sense ell, una ruta que
          cau al 404 o a un tab per defecte dona ZERO incompliments — i zero és el que volem
          veure. Va al contenidor de la llista, no al `<>` de fora, perquè el que s'audita és
          això i no la barra de pantalla. */}
      <div data-ftt-screen="encarrecs-llista" style={{ minWidth: 0, maxWidth: '100%' }}>
        {/* OBERTS · TANCATS · TOTS. El desplegable d'estat se'n va: obert i tancat no són un
            filtre entre molts, són les dues safates on viu la feina, i amagar-les dins d'un
            `select` les feia costar dos clics i una lectura. La resta de filtres (mena, client)
            es queden com estaven —aquells sí que són filtres. Els codis segueixen sortint de
            `/vocabulari/`; aquí només es fixa quin ordre tenen a la barra. */}
        <SubTabs items={tabs} actiu={statusF}
                 onTria={(k) => setParams({ status: k, page: undefined })} />

        <FilaIdentitat>
          <Comptador valor={count} total={total ?? count} etiqueta={t('workorders.entity')} />
          {/* Cerca per NOM del model, codi i client (search_fields del ViewSet). Va a la URL
              perquè un resultat de cerca es comparteix; el `load` ja porta 150 ms de coixí, o
              sigui que escriure no dispara una crida per lletra. */}
          <span style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <i className="ti ti-search" aria-hidden="true"
               style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)',
                        fontSize: 16, color: 'var(--text-soft)', pointerEvents: 'none' }} />
            <input type="search" value={searchF}
              onChange={e => setParams({ search: e.target.value, page: undefined })}
              placeholder={t('workorders.search_placeholder')}
              aria-label={t('workorders.search_placeholder')}
              style={{ ...camp, width: '100%', paddingLeft: 28 }} />
          </span>
          <select value={kindF} onChange={e => setParams({ kind: e.target.value, page: undefined })}
            aria-label={t('workorders.col_kind')} style={camp}>
            <option value="">{t('workorders.filter_kind_all')}</option>
            {(tipus || []).map(k => <option key={k} value={k}>{t(`workorders.kind_${k}`)}</option>)}
          </select>
          <select value={customerF} onChange={e => setParams({ customer: e.target.value, page: undefined })}
            aria-label={t('workorders.col_customer')} style={{ ...camp, flex: 1, minWidth: 180 }}>
            <option value="">{t('workorders.filter_customer_all')}</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </FilaIdentitat>

        {/* BARRA DE SELECCIÓ · només existeix quan hi ha alguna cosa triada. No és un peu fix ni
            un botó permanent apagat: una acció destructiva no ha d'estar sempre a la vista
            demanant que la premin. Diu QUANTS n'hi ha triats i ofereix desfer la tria. */}
        {triats.size > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
            padding: '8px 12px', marginBottom: 12,
            background: 'var(--sel)', borderWidth: 1, borderStyle: 'solid',
            borderColor: 'var(--line)', borderRadius: 'var(--r-card)',
            // §1 — la selecció és `--sel` MÉS filet d'or a l'esquerra. La vora daurada de la
            // volta sencera és el llenguatge de PORTA/secundari, no el de selecció, i aquesta
            // barra queda just sobre files que sí que porten el filet (`TaulaLlista:120`):
            // havien de parlar igual.
            boxShadow: 'inset 3px 0 0 var(--gold)',
          }}>
            <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
              {t('workorders.selected_n', { count: triats.size })}
            </span>
            <button type="button" onClick={() => setTriats(new Set())}
              style={{ border: 'none', background: 'none', cursor: 'pointer',
                       fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                       textDecoration: 'underline', padding: 0 }}>
              {t('workorders.clear_selection')}
            </button>
            <button type="button" onClick={passadaSeca} disabled={enviant}
              style={{ ...botoPri, marginLeft: 'auto' }}>
              <i className="ti ti-lock" aria-hidden="true" style={{ fontSize: 16 }} />
              {t('workorders.bulk_close_action')}
            </button>
          </div>
        )}

        {tancant && (
          <Modal
            nom="tancament-en-lot"
            title={t('workorders.bulk_close_title', { count: triats.size })}
            subtitle={
              previ === null ? t('workorders.bulk_close_comptant')
                : previ.error ? t('workorders.bulk_close_previ_error')
                  : t('workorders.bulk_close_body', {
                      tancables: previ.tancables,
                      bloquejats: previ.bloquejats,
                      deduibles: previ.deduibles,
                    })
            }
            confirmLabel={t('workorders.bulk_close_confirm')}
            cancelLabel={t('workorders.bulk_close_cancel')}
            // Fins que la passada seca no ha tornat, no hi ha res a confirmar.
            confirmDisabled={enviant || previ === null || !!previ.error}
            confirmVariant="destructiu"
            onConfirm={tancaSeleccionats}
            onCancel={() => { if (!enviant) { setTancant(false); setPrevi(null) } }}
          />
        )}

        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

        {loading ? <EstatBuit>{t('workorders.loading')}</EstatBuit>
          : error ? <EstatBuit>{t('workorders.error')}</EstatBuit>
            : items.length === 0 ? <EstatBuit>{t('workorders.empty')}</EstatBuit>
              : (
                /* `titolFila`: el número d'encàrrec ja no té columna —les sis són del MODEL— i
                   viu al `title` de la fila. Ningú l'escombra amb la vista; qui el té d'un
                   correu el busca amb el cercador, que hi cerca des del lot anterior. */
                <TaulaLlista cols={cols} files={items} clau={(r) => r.id}
                  ordre={ordre} onOrdenar={ordenar}
                  triada={(r) => triats.has(r.id)}
                  titolFila={(r) => r.number}
                  onObrir={(r) => navigate(`/comercial/encarrecs/${r.id}`)} />
              )}

        <Paginacio page={page} pages={pages} onPage={(p) => setParams({ page: p })}
          labelPrev={t('workorders.prev')} labelNext={t('workorders.next')}
          info={t('workorders.page_info', { page, pages })} />
      </div>
    </>
  )
}
