import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { garmentTypeItems, garmentPomMaps, poms } from '../../api/endpoints'
import { useEstatDiccionari } from '../../utils/diccionariMesuresFont'
import { dimensionsDe, composaInstancia, tramsInstancia } from '../../utils/diccionariMesures'
import { CAPES, etiquetaCapa, etiquetaInstancia } from '../../utils/capaInstancia'

// U2/R1 · LA GERMANA DE PRESENTACIÓ · «Talles i POMs» del catàleg de peces.
//
// ── PER QUÈ EXISTEIX, I PER QUÈ NO ÉS `EditableTable` ────────────────────────────────────────
// La v4 reprodueix la taula de «Definició de POMs» (`EditableTable`, 2.075 línies): el mateix
// desplegable de capa, les mateixes píndoles d'instància, les mateixes tecles L/I/N i el mateix
// cercador amb sufixos. Però `EditableTable` està ANCORADA AL MODEL —`modelId` com a prop, el
// desat per `models.setPomRegla`, el mode `presa` amb les seves portes de model— i el catàleg
// escriu a una altra taula: `GarmentPOMMap`, la pertinença de l'ITEM.
//
// Donar-li un segon backend intern seria posar dues fonts de veritat dins d'un component que ja
// en té prou. Per ordre d'Agus (patró VÀLVULA D'ESCAPAMENT) es construeix aquesta germana i
// **`EditableTable` no es toca ni una línia**.
//
// ── QUÈ ES COMPARTEIX (i no es duplica) ──────────────────────────────────────────────────────
// Tot el VOCABULARI, que ja vivia en mòduls purs de sprints anteriors — no ha calgut extreure
// res, només consumir-los:
//   · `utils/capaInstancia` → CAPES · etiquetaCapa · etiquetaInstancia
//   · `utils/diccionariMesures` → dimensionsDe · composaInstancia
//   · `utils/diccionariMesuresFont` → useEstatDiccionari (les capes i instàncies REALS de la BD)
// Així les paraules d'aquesta taula i les de la del model surten del mateix lloc: si la Montse
// sembra una instància nova, apareix a totes dues sense tocar codi.
//
// ── QUÈ ES REIMPLEMENTA, I PER QUÈ ───────────────────────────────────────────────────────────
// El CICLE DE VIDA DE LA FILA (alta, baixa, canvi d'identitat, desat). A `EditableTable` està
// entrellaçat amb el desat del model i amb el mode `presa`; aquí és molt més petit —una sola
// porta, `garmentPomMaps`, i un sol botó de desar— i extreure'l hauria demanat obrir el fitxer
// que aquest tram té prohibit tocar.

const MONO = 'IBM Plex Mono, monospace'

// 2 i 3 (Agus 19:35) · la mida es la del cos (Models) i el fons es BLANC: el crema de
// capcalera sobre el gris de pagina queda fora de tota la pantalla.
const th = {
  fontSize: 'var(--fs-body)', textTransform: 'uppercase', letterSpacing: '.05em',
  color: 'var(--text-muted)', fontWeight: 500, padding: '6px 10px',
  background: 'var(--white)', borderBottom: '0.5px solid var(--gray-l)',
  textAlign: 'left', verticalAlign: 'bottom', fontFamily: MONO,
}
const td = {
  padding: '4px 10px', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'middle',
  fontFamily: MONO, fontSize: 'var(--fs-body)',
}
const pindola = (activa) => ({
  border: `0.5px solid ${activa ? 'var(--gold)' : 'var(--gray-l)'}`,
  background: activa ? 'var(--gold-pale)' : 'var(--white)',
  color: activa ? 'var(--gold)' : 'var(--text-main)',
  fontWeight: activa ? 600 : 400,
  borderRadius: 6, padding: '2px 9px', fontFamily: MONO, fontSize: 'var(--fs-body)',
  cursor: 'pointer',
})
const iconaCel = {
  color: 'var(--gray)', cursor: 'pointer', background: 'none', border: 'none',
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: 0,
}

// La identitat d'una fila, que és la clau única de `GarmentPOMMap`.
const clau = (r) => `${r.pom_id}|${r.capa || 'exterior'}|${r.instancia || ''}`

export default function TaulaPOMsCataleg({ itemId, tallaBase, onDirty, onSaved, onError, onTornar }) {
  const { t } = useTranslation()
  const { dicc } = useEstatDiccionari()
  const [files, setFiles] = useState([])
  const [tretes, setTretes] = useState([])      // mapIds a esborrar en desar
  const [carregant, setCarregant] = useState(true)
  const [desant, setDesant] = useState(false)
  const refsValor = useRef({})

  const dims = dimensionsDe(dicc)
  const capesDelDiccionari = dicc?.capes?.length ? dicc.capes.map(c => c.slug) : CAPES

  // La llista arriba de l'ACUMULACIÓ (grup + família + item): és el catàleg que l'item PROPOSA,
  // i cada fila ja diu de quin nivell ve. Les de nivell grup/família no tenen `map_id` d'item:
  // desar-les és el gest que les fa pertinences PRÒPIES de l'item.
  const carrega = useCallback(async () => {
    if (!itemId) return
    setCarregant(true)
    try {
      const r = await garmentTypeItems.acumulacio(itemId)
      const poms_ = r.data?.poms || []
      setFiles(poms_.map((p, i) => ({
        id: `${p.nivell}-${p.map_id}`,
        mapId: p.nivell === 'item' ? p.map_id : null,
        nivell: p.nivell,
        pom_id: p.pom_id,
        pom_code: p.pom_code || '',
        // La v4 posa el nom ANGLÈS a la cel·la i deixa el CATALÀ darrere la ⓘ (el seu `title`
        // diu literalment «nom en català»). És el nom que viatja a la fitxa del fabricant.
        nom: p.name_en || p.name_cat || '',
        nom_ca: p.name_cat || '',
        capa: p.capa || 'exterior',
        instancia: p.instancia || '',
        ordre: i,
      })))
      setTretes([])
    } catch {
      onError?.(t('cataleg_peces.load_error'))
    } finally {
      setCarregant(false)
    }
  }, [itemId, onError, t])

  useEffect(() => { carrega() }, [carrega])

  const marca = () => onDirty?.(true)

  const canviaIdentitat = (id, camps) => {
    setFiles(prev => {
      const fila = prev.find(r => r.id === id)
      if (!fila) return prev
      const nova = { ...fila, ...camps }
      // La clau és única: moure una fila damunt d'una germana viva escriuria damunt seu en
      // silenci. Es refusa el gest i es diu, que és el que la casa ja va aprendre a C1.
      if (prev.some(r => r.id !== id && clau(r) === clau(nova))) {
        onError?.(t('cataleg_peces.dup_identitat'))
        return prev
      }
      return prev.map(r => (r.id === id ? nova : r))
    })
    marca()
  }

  // ⧉ DUPLICAR — la germana de capa de la maqueta: el mateix POM a la següent capa LLIURE.
  // «Lliure» i no «la següent»: la clau única és (item, pom, capa, instancia) i oferir-ne una de
  // presa escriuria damunt d'una fila existent.
  const duplica = (fila) => {
    setFiles(prev => {
      const preses = new Set(prev
        .filter(r => r.pom_id === fila.pom_id && (r.instancia || '') === (fila.instancia || ''))
        .map(r => r.capa || 'exterior'))
      const lliure = capesDelDiccionari.find(c => !preses.has(c))
      if (!lliure) { onError?.(t('cataleg_peces.sense_capa_lliure')); return prev }
      const idx = prev.findIndex(r => r.id === fila.id)
      const nova = { ...fila, id: `nova-${fila.pom_id}-${lliure}-${prev.length}`,
        mapId: null, nivell: 'item', capa: lliure }
      return [...prev.slice(0, idx + 1), nova, ...prev.slice(idx + 1)]
        .map((r, i) => ({ ...r, ordre: i }))
    })
    marca()
  }

  const treu = (fila) => {
    setFiles(prev => prev.filter(r => r.id !== fila.id).map((r, i) => ({ ...r, ordre: i })))
    if (fila.mapId) setTretes(prev => [...prev, fila.mapId])
    marca()
  }

  const afegeix = (pom, eixos = {}) => {
    setFiles(prev => {
      const nova = {
        id: `nova-${pom.id}-${prev.length}`, mapId: null, nivell: 'item',
        pom_id: pom.id, pom_code: pom.codi_client || '',
        nom: pom.nom_client || pom.nom_ca || pom.nom_en || '',
        capa: eixos.capa || 'exterior', instancia: eixos.instancia || '', ordre: prev.length,
      }
      if (prev.some(r => clau(r) === clau(nova))) {
        onError?.(t('cataleg_peces.dup_identitat'))
        return prev
      }
      return [...prev, nova]
    })
    marca()
  }

  // El desat: les baixes primer (una identitat que se'n va ha de deixar lliure la seva clau
  // abans que una altra fila la reclami), i després les altes i els ordres.
  const desa = async () => {
    setDesant(true)
    try {
      for (const mapId of tretes) await garmentPomMaps.remove(mapId)
      for (const r of files) {
        const cos = {
          garment_type_item: itemId, pom: r.pom_id,
          capa: r.capa || 'exterior', instancia: r.instancia || '', ordre: r.ordre,
        }
        if (r.mapId) await garmentPomMaps.update(r.mapId, cos)
        else await garmentPomMaps.create(cos)
      }
      await carrega()
      onDirty?.(false)
      onSaved?.()
    } catch (e) {
      onError?.(e?.response?.data?.detail || t('cataleg_peces.save_error'))
    } finally {
      setDesant(false)
    }
  }

  // ── LES TECLES DE LA MAQUETA ────────────────────────────────────────────────────────────────
  // ↓/Enter següent · ↑ anterior · L germana de capa · I grups d'instància · N nomenclatura.
  // Van al carril de valors, que és on viu el focus mentre s'omple la taula.
  const tecles = (e, fila, idx) => {
    const anar = (n) => {
      const seguent = files[n]
      if (seguent) refsValor.current[seguent.id]?.focus()
    }
    if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); anar(idx + 1) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); anar(idx - 1) }
    else if (e.key === 'l' || e.key === 'L') { e.preventDefault(); duplica(fila) }
  }

  const capçalera = useMemo(() => dims.map(d => d.clau), [dims])

  if (carregant) return <div style={{ padding: 16, color: 'var(--text-muted)', fontFamily: MONO }}>{t('cataleg_peces.loading')}</div>

  return (
    <div>
      <div style={{
        padding: '7px 14px', borderBottom: '0.5px solid var(--gray-l)',
        fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontFamily: MONO,
      }}>
        <Kbd>↓</Kbd>/<Kbd>Enter</Kbd> {t('cataleg_peces.keys_next')} · <Kbd>↑</Kbd> {t('cataleg_peces.keys_prev')} ·{' '}
        <Kbd>L</Kbd> {t('cataleg_peces.keys_layer_sibling')} · <Kbd>I</Kbd> {t('cataleg_peces.keys_instance')} ·{' '}
        <Kbd>N</Kbd> {t('cataleg_peces.keys_nomenclature')} · {t('cataleg_peces.keys_finder')} <Kbd>↓</Kbd> {t('cataleg_peces.keys_finder_end')}
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'separate', borderSpacing: 0, minWidth: 1060, tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: 44 }} /><col style={{ width: 104 }} /><col style={{ width: 40 }} />
            <col style={{ width: 86 }} /><col style={{ width: 236 }} /><col style={{ width: 130 }} />
            <col style={{ width: 166 }} /><col style={{ width: 46 }} /><col style={{ width: 110 }} />
            <col style={{ width: 42 }} />
          </colgroup>
          <thead>
            <tr>
              <th style={th} colSpan={5} />
              <th style={{ ...th, textAlign: 'center', color: 'var(--gold)', fontWeight: 600 }} colSpan={3}>
                {t('cataleg_peces.th_instance')}
              </th>
              <th style={{ ...th, textAlign: 'right', color: 'var(--gold)', fontWeight: 600 }} rowSpan={2}>
                {t('cataleg_peces.th_base_measure')}
                <b style={{ display: 'block', fontSize: 'var(--fs-h3)' }}>{tallaBase || '—'}</b>
              </th>
              <th style={th} rowSpan={2} />
            </tr>
            <tr>
              <th style={th}>{t('cataleg_peces.th_num')}</th>
              <th style={th}>{t('cataleg_peces.th_layer')}</th>
              <th style={th} />
              <th style={th}>{t('cataleg_peces.th_pom')}</th>
              <th style={th}>{t('cataleg_peces.th_name')}</th>
              <th style={{ ...th, textAlign: 'center' }}>{t('cataleg_peces.th_position')}</th>
              <th style={{ ...th, textAlign: 'center' }}>{t('cataleg_peces.th_state')}</th>
              <th style={{ ...th, textAlign: 'center' }}>{t('cataleg_peces.th_more')}</th>
            </tr>
          </thead>
          <tbody>
            {files.map((r, i) => (
              <Fila key={r.id} r={r} i={i} t={t} dicc={dicc} dims={dims}
                capes={capesDelDiccionari} eixos={capçalera}
                refValor={(el) => { refsValor.current[r.id] = el }}
                onTecla={(e) => tecles(e, r, i)}
                onCapa={(capa) => canviaIdentitat(r.id, { capa })}
                onInstancia={(instancia) => canviaIdentitat(r.id, { instancia })}
                onDuplica={() => duplica(r)}
                onTreu={() => treu(r)} />
            ))}
          </tbody>
        </table>
      </div>

      <CercadorPOM t={t} dicc={dicc} onTria={afegeix} />

      <div style={{
        padding: '10px 14px', borderTop: '0.5px solid var(--gray-l)', background: 'var(--white)',
        display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
      }}>
        <button style={btnPeu}>{t('cataleg_peces.import_from_sheet')}</button>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontFamily: MONO }}>
          {t('cataleg_peces.seed_note')}
        </span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          {/* El «Tornar» de la v4 va AL CATÀLEG (`tanca()`), no enrere a l'historial: entrant per
              URL directa, un `history.back()` se'n duria l'usuari fora de l'aplicació. */}
          <button style={btnPeu} onClick={onTornar}>{t('cataleg_peces.back')}</button>
          <button style={{ ...btnPeu, background: 'var(--gold)', borderColor: 'var(--gold)', color: 'var(--white)', fontWeight: 600 }}
            disabled={desant} onClick={desa}>{t('cataleg_peces.save')}</button>
        </span>
      </div>
    </div>
  )
}

const btnPeu = {
  border: '0.5px solid var(--gray-l)', background: 'var(--white)', color: 'var(--text-main)',
  borderRadius: 6, padding: '6px 12px', fontFamily: MONO, fontSize: 'var(--fs-body)',
  cursor: 'pointer', whiteSpace: 'nowrap',
}

function Kbd({ children }) {
  return (
    <kbd style={{
      border: '0.5px solid var(--gray-l)', borderRadius: 3, padding: '1px 5px',
      background: 'var(--white)', fontFamily: MONO, fontSize: 'var(--fs-body)',
    }}>{children}</kbd>
  )
}

function Fila({ r, i, t, dicc, dims, capes, refValor, onTecla, onCapa, onInstancia, onDuplica, onTreu }) {
  // Les píndoles de cada eix surten de la BD (D-31.26): un grup per eix i, dins, les seves files
  // pel `display_order`. Amb el diccionari en vol la llista és buida i la taula es pinta igual.
  // El slug compost es parteix amb el SEPARADOR del diccionari, no amb un guió escrit aquí.
  const trams = tramsInstancia(dicc, r.instancia)
  const commuta = (slug) => {
    // Dins d'un eix les opcions són excloents: triar «right» treu «left», no les suma.
    const eix = dims.find(d => d.opcions.some(o => o.slug === slug))
    const altres = trams.filter(x => !eix?.opcions.some(o => o.slug === x))
    const nous = trams.includes(slug) ? altres : [...altres, slug]
    onInstancia(composaInstancia(dicc, nous) || '')
  }

  return (
    <tr>
      <td style={{ ...td, color: 'var(--gray)' }}>{i + 1}</td>
      <td style={td}>
        <select value={r.capa || 'exterior'} onChange={e => onCapa(e.target.value)}
          style={{
            fontFamily: MONO, fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)',
            borderRadius: 5, padding: '3px 6px', background: 'var(--white)', width: '100%',
            color: 'var(--text-main)',
          }}>
          {capes.map(c => <option key={c} value={c}>{etiquetaCapa(c, t)}</option>)}
        </select>
      </td>
      <td style={td}>
        <button type="button" style={iconaCel} title={t('cataleg_peces.title_duplicate')} onClick={onDuplica}>⧉</button>
      </td>
      <td style={{ ...td, color: 'var(--gold)', fontWeight: 600 }}>{r.pom_code}</td>
      <td style={{ ...td, lineHeight: 1.4 }}>
        {r.nom}
        <span style={{ ...iconaCel, marginLeft: 5, fontSize: 'var(--fs-body)' }}
          title={r.nom_ca ? `${t('cataleg_peces.title_name_ca')}: ${r.nom_ca}` : t('cataleg_peces.title_name_ca')}>ⓘ</span>
        <span style={{ ...iconaCel, marginLeft: 5, fontSize: 'var(--fs-body)' }} title={t('cataleg_peces.title_edit_name')}>✎</span>
      </td>
      {/* Els dos primers eixos del diccionari són les dues columnes que la v4 dibuixa (Posició ·
          Estat), i de cada eix se n'ensenyen les DUES PRIMERES opcions — exactament el que fa
          la taula del model (`EditableTable`: `d.opcions.slice(0, 2)`). Les dues píndoles de la
          maqueta NO són dades de demostració: són la llei de la casa. La resta del vocabulari
          (el diccionari en porta vuit a l'eix de posició) viu darrere el `＋`, que és la seva
          porta; posar-les totes en línia faria files de vuit ratlles d'alt. */}
      {[0, 1].map(k => {
        const d = dims[k]
        return (
          <td key={d?.clau || `buit-${k}`} style={td}>
            {d && (
              <span style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                {d.opcions.slice(0, 2).map(o => (
                  <button key={o.slug} type="button" style={pindola(trams.includes(o.slug))}
                    onClick={() => commuta(o.slug)}>{etiquetaInstancia(o.slug, dicc)}</button>
                ))}
              </span>
            )}
          </td>
        )
      })}
      <td style={{ ...td, textAlign: 'center' }}>
        <button type="button" style={pindola(false)} title={t('cataleg_peces.th_more')}>＋</button>
      </td>
      <td style={{ ...td, background: 'var(--gold-pale)', textAlign: 'right' }}>
        <input ref={refValor} onKeyDown={onTecla} placeholder="—"
          style={{
            width: 92, textAlign: 'right', fontSize: 'var(--fs-body)', fontWeight: 600,
            fontFamily: MONO, border: '0.5px solid var(--gray-l)', borderRadius: 5,
            padding: '3px 8px', background: 'var(--white)', color: 'var(--text-main)',
          }} />
      </td>
      <td style={td}>
        <button type="button" style={iconaCel} title={t('cataleg_peces.title_remove')} onClick={onTreu}>✕</button>
      </td>
    </tr>
  )
}

// El cercador del peu, amb els sufixos d'identitat de la maqueta: «C.f» → capa folre,
// «S.l» → instància left. La regla de composició del codi la posa el diccionari, no aquest fitxer.
function CercadorPOM({ t, dicc, onTria }) {
  const [q, setQ] = useState('')
  const [resultats, setResultats] = useState([])

  const { text, eixos } = useMemo(() => separaSufixos(q, dicc), [q, dicc])

  useEffect(() => {
    if (text.length < 2) { setResultats([]); return undefined }
    const timer = setTimeout(() => {
      poms.cerca({ q: text, page_size: 10 })
        .then(r => setResultats(r.data?.results ?? r.data ?? []))
        .catch(() => setResultats([]))
    }, 300)
    return () => clearTimeout(timer)
  }, [text])

  return (
    <div style={{ padding: '8px 14px', borderTop: '0.5px solid var(--gray-l)', position: 'relative' }}>
      <input value={q} onChange={e => setQ(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && resultats[0]) {
            onTria(resultats[0], eixos); setQ(''); setResultats([])
          }
          if (e.key === 'Escape') { setQ(''); setResultats([]) }
        }}
        placeholder={t('cataleg_peces.finder_placeholder')}
        style={{
          width: 330, fontFamily: MONO, fontSize: 'var(--fs-body)',
          border: '0.5px solid var(--gold)', borderRadius: 5, padding: '5px 9px',
          background: 'var(--white)', color: 'var(--text-main)',
        }} />
      <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginLeft: 9, fontFamily: MONO }}>
        {t('cataleg_peces.finder_hint')}
      </span>
      {resultats.length > 0 && (
        <div style={{
          position: 'absolute', bottom: '100%', left: 14, marginBottom: 4, zIndex: 100,
          background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 6,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)', minWidth: 300,
        }}>
          {resultats.map(p => (
            <button key={p.id} type="button"
              onClick={() => { onTria(p, eixos); setQ(''); setResultats([]) }}
              style={{
                display: 'block', width: '100%', textAlign: 'left', border: 'none',
                background: 'transparent', padding: '6px 12px', cursor: 'pointer',
                fontFamily: MONO, fontSize: 'var(--fs-body)',
                borderBottom: '0.5px solid var(--gray-l)',
              }}>
              <span style={{ color: 'var(--gold)', marginRight: 8 }}>{p.codi_client}</span>
              {p.nom_client || p.nom_ca || p.nom_en}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// «C.f» → {capa:'folre'} · «S.l» → {instancia:'left'}. El sufix és l'INICIAL del slug dins del
// seu vocabulari; ambigu o desconegut, s'ignora i el text va sencer a la cerca.
function separaSufixos(q, dicc) {
  const m = String(q).match(/^(.*?)\s+([CS])\.([a-z]+)$/i)
  if (!m) return { text: q.trim(), eixos: {} }
  const [, base, tipus, sufix] = m
  // `dicc.instancies` és un OBJECTE per eix ({posicio:[…], estat:[…]}), no una llista: s'aplana.
  const llista = tipus.toUpperCase() === 'C'
    ? (dicc?.capes?.length ? dicc.capes.map(c => c.slug) : CAPES)
    : Object.values(dicc?.instancies || {}).flat().map(o => o.slug)
  const trobat = llista.filter(s => s.startsWith(sufix.toLowerCase()))
  if (trobat.length !== 1) return { text: q.trim(), eixos: {} }
  return {
    text: base.trim(),
    eixos: tipus.toUpperCase() === 'C' ? { capa: trobat[0] } : { instancia: trobat[0] },
  }
}
