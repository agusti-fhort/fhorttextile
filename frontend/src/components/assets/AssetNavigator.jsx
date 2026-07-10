import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { garmentTypeItems, garmentTypes, itemFitxers, modelFitxers, models as modelsApi } from '../../api/endpoints'
import FileList from './FileList'

// AssetNavigator (S03c · C4) — el navegador únic dels dos mons d'actius del tenant.
//
//   mode='files'   → onPick(fitxer)  · un ModelFitxer (porta `model`) o un ItemFitxer (porta
//                    `garment_type_item`). El consumidor distingeix l'un de l'altre pel propi
//                    objecte i decideix què fer-ne: aquest component NO crida mai `usar-al-model`.
//   mode='models'  → onPick(model)   · per a TechSheetEntry.
//
// `inline` el treu del modal (TechSheetEntry és la pàgina sencera, no una capa a sobre).
//
// D20 — les FACETES DE MODELS es deriven AL CLIENT. Amb 20 models, 2 clients, 3 temporades i 2
// anys, l'agregació server-side seria correcció d'arquitectura, no necessitat de volum; i no
// existeix cap endpoint facetat (DIAGNOSI_S03C_NAVEGACIO Q1.3). `PAGE_MODELS` va per sota del
// `max_page_size=200` de DefaultPagination: si un dia el tenant creix, això s'ha de convertir en
// agregació al servidor, no en una pàgina més gran.
const PAGE_MODELS = 200
const MONO = 'IBM Plex Mono, monospace'
const DEBOUNCE_MS = 250   // el mateix que TechSheetEntry.jsx:59-62

const llista = (r) => (Array.isArray(r.data) ? r.data : (r.data?.results ?? []))
const uniq = (xs) => [...new Set(xs.filter(v => v !== null && v !== undefined && v !== ''))]

// Carregadors a l'àmbit del mòdul: han de ser estables per poder ser la dependència d'`useLlista`.
const CARREGA = {
  gts: () => garmentTypes.list({ actiu: true }),
  gtis: (gtId) => garmentTypeItems.list({ garment_type: gtId }),
  cerca: (q) => garmentTypeItems.list({ search: q }),
  fitxers: (clau) => {
    const [mon, id] = clau.split(':')
    return mon === 'm'
      ? modelFitxers.list({ model: id, is_current: true, ordering: '-data_pujada' })
      : itemFitxers.list({ garment_type_item: id, is_current: true, ordering: '-data_pujada' })
  },
}

// Resultat LLIGAT a la clau que el va demanar. Mentre `res.clau !== clau` encara carreguem →
// retorna null (= "carregant"). Així no s'ensenyen mai les files de la carpeta anterior mentre
// arriben les de la nova, i cap effect no crida `setState` de manera síncrona.
function useLlista(clau, carrega) {
  const [res, setRes] = useState({ clau: undefined, rows: null })
  useEffect(() => {
    if (clau === null || clau === undefined) return undefined
    let viu = true
    carrega(clau)
      .then(r => { if (viu) setRes({ clau, rows: llista(r) }) })
      .catch(() => { if (viu) setRes({ clau, rows: [] }) })
    return () => { viu = false }
  }, [clau, carrega])
  if (clau === null || clau === undefined) return null
  return res.clau === clau ? res.rows : null
}

const cap = {
  background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: MONO,
  fontSize: 'var(--fs-body)', color: 'var(--text-muted)', padding: '2px 4px',
}

function Carpeta({ icona, titol, subtitol, comptador, onClick, onDoubleClick, actiu = false }) {
  return (
    <button type="button" onClick={onClick} onDoubleClick={onDoubleClick} aria-current={actiu || undefined} style={{
      display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'left',
      padding: '10px 12px', cursor: 'pointer', fontFamily: MONO,
      background: actiu ? 'var(--gold-pale)' : 'transparent',
      border: 'none', borderBottom: '0.5px solid var(--border)',
    }}>
      <i className={`ti ${icona}`} aria-hidden="true" style={{ fontSize: 18, color: 'var(--gold)', flexShrink: 0 }} />
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: 'block', fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: actiu ? 700 : 500 }}>{titol}</span>
        {subtitol && <span style={{ display: 'block', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{subtitol}</span>}
      </span>
      {comptador !== undefined && (
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{comptador}</span>
      )}
      <i className="ti ti-chevron-right" aria-hidden="true" style={{ color: 'var(--text-muted)' }} />
    </button>
  )
}

export default function AssetNavigator({
  mode = 'files', filterTipus = null, onPick, onClose, inline = false,
  actionLabel, pickable, nav: navExtern, onNav: onNavExtern,
}) {
  const { t } = useTranslation()

  // Memòria de camí: si el consumidor la puja a estat de pàgina, el camí sobreviu a tancar i
  // reobrir el navegador. Mai localStorage — és context de sessió, no preferència d'usuari.
  const [navIntern, setNavIntern] = useState({ tab: 'models', cust: null, any: null, temp: null, modelId: null, gtId: null, gtiId: null })
  const nav = navExtern ?? navIntern
  const setNav = onNavExtern ?? setNavIntern
  const patch = (p) => setNav({ ...nav, ...p })

  const [query, setQuery] = useState('')
  const [cerca, setCerca] = useState('')          // query amb debounce aplicat
  const [modelsTots, setModelsTots] = useState(null)
  const [triatRaw, setTriatRaw] = useState(null)

  useEffect(() => {
    const id = setTimeout(() => setCerca(query.trim()), DEBOUNCE_MS)
    return () => clearTimeout(id)
  }, [query])

  // Els models es carreguen UN cop: són la base de les facetes del client (D20) i de la llista.
  useEffect(() => {
    modelsApi.list({ page_size: PAGE_MODELS, ordering: '-data_entrada' })
      .then(r => setModelsTots(llista(r))).catch(() => setModelsTots([]))
  }, [])

  // Cerca global: travessa els dos mons alhora. Els models ja els tenim (filtrat local sobre els
  // mateixos camps que `ModelViewSet.search_fields`); els GTI van al servidor (search de C2.2).
  const resCatalegCerca = useLlista(cerca && mode === 'files' ? cerca : null, CARREGA.cerca)

  const modelsTrobats = useMemo(() => {
    if (!cerca || !modelsTots) return []
    const q = cerca.toLowerCase()
    return modelsTots.filter(m => [m.codi_intern, m.codi_client, m.nom_prenda]
      .some(v => (v || '').toLowerCase().includes(q)))
  }, [cerca, modelsTots])

  const gts = useLlista(nav.tab === 'catalog' ? 'gt' : null, CARREGA.gts)
  const gtis = useLlista(nav.gtId ?? null, CARREGA.gtis)

  // Fitxers del node fulla. `is_current=true`: el navegador ensenya el CAP de cada cadena de
  // versions, no l'historial — l'historial viu al tab Fitxers de ModelSheet.
  const clauNode = mode === 'models' ? null
    : nav.modelId ? `m:${nav.modelId}` : nav.gtiId ? `i:${nav.gtiId}` : null
  const fitxers = useLlista(clauNode, CARREGA.fitxers)

  // La selecció també va lligada al node: en canviar de carpeta el peu no pot seguir oferint
  // "Utilitza" sobre un fitxer que ja no és a la vista.
  const triat = triatRaw?.clau === clauNode ? triatRaw.f : null
  const setTriat = useCallback((f) => setTriatRaw({ clau: clauNode, f }), [clauNode])

  const fitxersVisibles = useMemo(() => {
    if (!fitxers || !filterTipus?.length) return fitxers
    return fitxers.filter(f => filterTipus.includes(f.tipus))
  }, [fitxers, filterTipus])

  // ── Facetes derivades al client (D20) ────────────────────────────────────
  const clients = useMemo(() => {
    if (!modelsTots) return []
    return uniq(modelsTots.map(m => m.customer_nom)).sort()
  }, [modelsTots])
  const perClient = useMemo(() => (modelsTots || []).filter(m => m.customer_nom === nav.cust), [modelsTots, nav.cust])
  const anys = useMemo(() => uniq(perClient.map(m => m.any)).sort((a, b) => b - a), [perClient])
  const perAny = useMemo(() => perClient.filter(m => String(m.any) === String(nav.any)), [perClient, nav.any])
  const temporades = useMemo(() => uniq(perAny.map(m => m.temporada)).sort(), [perAny])
  const perTemporada = useMemo(() => perAny.filter(m => m.temporada === nav.temp), [perAny, nav.temp])

  const modelDe = useCallback((id) => (modelsTots || []).find(m => m.id === id), [modelsTots])
  const gtiDe = useCallback((id) => (gtis || []).find(g => g.id === id), [gtis])

  // En mode='models' un model és una FULLA seleccionable (el peu la confirma), no una carpeta on
  // s'entra: no hi ha res a dins que aquest mode sàpiga ensenyar. En mode='files' sí que s'hi entra.
  const anarAModel = (m) => patch({
    tab: 'models', cust: m.customer_nom, any: m.any, temp: m.temporada, modelId: m.id, gtId: null, gtiId: null,
  })
  const anarAGti = (gti) => patch({ tab: 'catalog', gtId: gti.garment_type, gtiId: gti.id, modelId: null })

  // ── Breadcrumb ───────────────────────────────────────────────────────────
  const molles = []
  if (nav.tab === 'models') {
    molles.push({ txt: t('asset_navigator.tab_models'), go: () => patch({ cust: null, any: null, temp: null, modelId: null }) })
    if (nav.cust) molles.push({ txt: nav.cust, go: () => patch({ any: null, temp: null, modelId: null }) })
    if (nav.any) molles.push({ txt: String(nav.any), go: () => patch({ temp: null, modelId: null }) })
    if (nav.temp) molles.push({ txt: nav.temp, go: () => patch({ modelId: null }) })
    // En mode='models' el model és una selecció, no una ubicació: no és una molla del camí.
    if (nav.modelId && mode === 'files') molles.push({ txt: modelDe(nav.modelId)?.codi_intern || '…', go: null })
  } else {
    molles.push({ txt: t('asset_navigator.tab_catalog'), go: () => patch({ gtId: null, gtiId: null }) })
    if (nav.gtId) molles.push({ txt: (gts || []).find(g => g.id === nav.gtId)?.codi_client || '…', go: () => patch({ gtiId: null }) })
    if (nav.gtiId) molles.push({ txt: gtiDe(nav.gtiId)?.code || '…', go: null })
  }

  // El doble clic de FileList ha de respectar el mateix guard que el peu.
  const obrirFitxer = (f) => { if (!pickable || pickable(f)) onPick?.(f) }

  // ── Cos ──────────────────────────────────────────────────────────────────
  let cos
  if (cerca) {
    cos = (
      <div>
        <Secció titol={t('asset_navigator.group_models', { n: modelsTrobats.length })} />
        {modelsTrobats.length === 0
          ? <Buit txt={t('asset_navigator.no_results')} />
          : modelsTrobats.map(m => (
            <Carpeta key={`m${m.id}`} icona="ti-file-text" titol={m.codi_intern}
              subtitol={[m.nom_prenda, m.customer_nom].filter(Boolean).join(' · ')}
              actiu={mode === 'models' && nav.modelId === m.id}
              onClick={() => anarAModel(m)}
              onDoubleClick={mode === 'models' ? () => onPick?.(m) : undefined} />
          ))}
        {mode === 'files' && (<>
          <Secció titol={t('asset_navigator.group_catalog', { n: resCatalegCerca?.length ?? 0 })} />
          {resCatalegCerca === null
            ? <Buit txt={t('app.loading')} />
            : resCatalegCerca.length === 0
              ? <Buit txt={t('asset_navigator.no_results')} />
              : resCatalegCerca.map(g => (
                <Carpeta key={`g${g.id}`} icona="ti-layers-intersect" titol={g.code} subtitol={g.name}
                  comptador={g.fitxers_count} onClick={() => anarAGti(g)} />
              ))}
        </>)}
      </div>
    )
  } else if (nav.tab === 'models') {
    if (nav.modelId && mode === 'files') cos = <FileList files={fitxersVisibles} selectedId={triat?.id} onSelect={setTriat} onOpen={obrirFitxer} />
    else if (nav.temp) cos = perTemporada.map(m => (
      <Carpeta key={m.id} icona="ti-file-text" titol={m.codi_intern} subtitol={m.nom_prenda}
        actiu={mode === 'models' && nav.modelId === m.id}
        onClick={() => anarAModel(m)}
        onDoubleClick={mode === 'models' ? () => onPick?.(m) : undefined} />
    ))
    else if (nav.any) cos = temporades.map(s => <Carpeta key={s} icona="ti-folder" titol={s} onClick={() => patch({ temp: s })} />)
    else if (nav.cust) cos = anys.map(a => <Carpeta key={a} icona="ti-folder" titol={String(a)} onClick={() => patch({ any: a })} />)
    else if (!modelsTots) cos = <Buit txt={t('app.loading')} />
    else cos = clients.map(c => (
      <Carpeta key={c} icona="ti-folder" titol={c}
        comptador={modelsTots.filter(m => m.customer_nom === c).length}
        onClick={() => patch({ cust: c })} />
    ))
  } else {
    if (nav.gtiId) cos = <FileList files={fitxersVisibles} selectedId={triat?.id} onSelect={setTriat} onOpen={obrirFitxer} />
    else if (nav.gtId) cos = gtis === null ? <Buit txt={t('app.loading')} /> : gtis.map(g => (
      <Carpeta key={g.id} icona="ti-layers-intersect" titol={g.code} subtitol={g.name}
        comptador={g.fitxers_count} onClick={() => patch({ gtiId: g.id })} />
    ))
    else cos = gts === null ? <Buit txt={t('app.loading')} /> : gts.map(g => (
      <Carpeta key={g.id} icona="ti-folder" titol={g.codi_client} subtitol={g.nom_client}
        comptador={g.items_count} onClick={() => patch({ gtId: g.id })} />
    ))
  }

  // `pickable` deshabilita el peu per als fitxers que el consumidor no sap inserir (p.ex. un PDF
  // al canvas). Val més un botó apagat que un error DESPRÉS d'haver-ne fet ja la còpia sobirana.
  const potConfirmar = mode === 'models'
    ? !!nav.modelId
    : !!triat && (!pickable || pickable(triat))

  const cosNavegador = (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}>
      {/* 1 · cerca global, sempre visible */}
      <div style={{ padding: '10px 12px', borderBottom: '0.5px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, border: '0.5px solid var(--border)', borderRadius: 6, padding: '6px 10px', background: 'var(--white)' }}>
          <i className="ti ti-search" aria-hidden="true" style={{ color: 'var(--text-muted)' }} />
          <input value={query} onChange={e => setQuery(e.target.value)}
            placeholder={mode === 'models' ? t('asset_navigator.search_models') : t('asset_navigator.search_all')}
            aria-label={t('asset_navigator.search_all')}
            style={{ flex: 1, border: 'none', outline: 'none', fontFamily: MONO, fontSize: 'var(--fs-body)', background: 'transparent', color: 'var(--text-main)' }} />
          {query && (
            <button type="button" onClick={() => setQuery('')} aria-label={t('app.close')} style={{ ...cap, padding: 0 }}>
              <i className="ti ti-x" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* 2 · fork de dos mons + breadcrumb (amagats mentre la cerca global mana) */}
      {!cerca && (
        <div style={{ flexShrink: 0 }}>
          {mode === 'files' && (
            <div style={{ display: 'flex', borderBottom: '0.5px solid var(--border)' }}>
              {['models', 'catalog'].map(tb => (
                <button key={tb} type="button" onClick={() => patch({ tab: tb })}
                  style={{
                    flex: 1, padding: '8px 4px', cursor: 'pointer', fontFamily: MONO, border: 'none',
                    fontSize: 'var(--fs-body)', background: nav.tab === tb ? 'var(--gold-pale)' : 'transparent',
                    color: nav.tab === tb ? 'var(--gold)' : 'var(--text-muted)',
                    borderBottom: `2px solid ${nav.tab === tb ? 'var(--gold)' : 'transparent'}`,
                  }}>
                  {t(`asset_navigator.tab_${tb}`)}
                </button>
              ))}
            </div>
          )}
          <nav aria-label={t('asset_navigator.breadcrumb')} style={{ display: 'flex', alignItems: 'center', gap: 2, padding: '6px 12px', flexWrap: 'wrap', borderBottom: '0.5px solid var(--border)' }}>
            {molles.map((m, i) => (
              <span key={i} style={{ display: 'inline-flex', alignItems: 'center' }}>
                {i > 0 && <i className="ti ti-chevron-right" aria-hidden="true" style={{ color: 'var(--text-muted)', fontSize: 12 }} />}
                {m.go
                  ? <button type="button" onClick={m.go} style={{ ...cap, color: 'var(--gold)' }}>{m.txt}</button>
                  : <span style={{ ...cap, color: 'var(--text-main)', fontWeight: 600 }}>{m.txt}</span>}
              </span>
            ))}
          </nav>
        </div>
      )}

      {/* 3 · cos navegable */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>{cos}</div>

      {/* 4 · peu contextual */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
        borderTop: '0.5px solid var(--border)', flexShrink: 0, background: 'var(--bg-muted)',
      }}>
        <span style={{ flex: 1, minWidth: 0, fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {mode === 'models'
            ? (nav.modelId ? modelDe(nav.modelId)?.codi_intern : t('asset_navigator.pick_model'))
            : (triat ? triat.nom_fitxer : t('asset_navigator.pick_file'))}
        </span>
        {onClose && (
          <button type="button" onClick={onClose} style={{ ...cap, border: '0.5px solid var(--border)', borderRadius: 5, padding: '5px 12px', color: 'var(--text-main)' }}>
            {t('app.cancel')}
          </button>
        )}
        <button type="button" disabled={!potConfirmar}
          onClick={() => onPick?.(mode === 'models' ? modelDe(nav.modelId) : triat)}
          style={{
            border: 'none', borderRadius: 5, padding: '6px 14px', fontFamily: MONO,
            fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--white)', background: 'var(--gold)',
            cursor: potConfirmar ? 'pointer' : 'default', opacity: potConfirmar ? 1 : 0.45,
          }}>
          {actionLabel || t('asset_navigator.use')}
        </button>
      </div>
    </div>
  )

  if (inline) {
    return (
      <div style={{ border: '0.5px solid var(--border)', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '60vh', background: 'var(--white)' }}>
        {cosNavegador}
      </div>
    )
  }

  return (
    <div onClick={onClose} role="presentation" style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 60,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div role="dialog" aria-modal="true" aria-label={t('asset_navigator.title')}
        onClick={e => e.stopPropagation()} style={{
          background: 'var(--white)', borderRadius: 12, width: 900, maxWidth: '94vw',
          height: 620, maxHeight: '88vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '0.5px solid var(--border)', flexShrink: 0 }}>
          <span style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('asset_navigator.title')}</span>
          <button type="button" onClick={onClose} aria-label={t('app.close')} style={{ ...cap, fontSize: 18 }}>
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>
        {cosNavegador}
      </div>
    </div>
  )
}

const Secció = ({ titol }) => (
  <div style={{
    padding: '6px 12px', fontFamily: MONO, fontSize: 'var(--fs-caption)', textTransform: 'uppercase',
    letterSpacing: '0.05em', color: 'var(--text-muted)', background: 'var(--bg-muted)',
  }}>{titol}</div>
)

const Buit = ({ txt }) => (
  <div style={{ padding: 20, textAlign: 'center', fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic' }}>{txt}</div>
)
