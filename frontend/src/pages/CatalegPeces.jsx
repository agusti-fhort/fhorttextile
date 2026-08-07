import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import {
  garmentTypes, garmentTypeItems, garmentGroups, itemFitxers,
  garmentGroupPomMaps, garmentTypePomMaps,
} from '../api/endpoints'
import { useGarmentGroups } from '../components/grading/garmentCatalog'
import { nomLocal } from '../components/grading/gradingAxes'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import { selS } from '../components/ui/buttons'

// U2 · CATÀLEG DE PECES — la cascada grup › família › item, segons `maqueta_cataleg_peces_v4.html`.
//
// PER QUÈ NO ÉS `CascadeFinder`, que és el navegador de catàleg de la casa. Perquè la seva
// columna 3 és una COLUMNA DE FINDER (una fila per ítem, amb un nus a la dreta) i la v4 la
// substitueix a posta per una TAULA de sis columnes alineades — «els items són línies, no
// pastilles» és literalment el que la v4 canvia respecte de la v3. `CascadeFinder` reparteix les
// tres columnes a `1fr 1fr 1fr`, no porta cerca per columna ni peu d'alta, i el seu nus dret és
// un comptador, no cinc cel·les. No hi ha manera de fer-li pintar això.
//
// El que SÍ que es comparteix, que és el que tanca el veto dels dos sistemes: **la font de
// dades i el vocabulari**. Grups per `useGarmentGroups` (el mateix registre de `/garment-groups/`,
// la mateixa normalització i el mateix ordre canònic que la cascada del wizard) i noms per
// `nomLocal`. Cap segona llista de grups, cap segon ordre, cap segona traducció.
//
// ⚠️ ESTATS QUE LA MAQUETA NO COBREIX (declarat al report): la v4 no dibuixa ni càrrega ni error,
// i aquesta pantalla és tota asíncrona. S'usa el bastiment que la casa ja té —`Center` i
// `Feedback`—, sense cap vocabulari visual nou. Pendent de confirmació d'Agus.

const MONO = 'IBM Plex Mono, monospace'

const COLS = '1fr 190px 148px 96px 104px 92px'   // la graella d'`.irow`/`.irowhead` de la v4

const panel = {
  background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 9,
  overflow: 'hidden',
}
const colhead = {
  padding: '9px 13px', background: 'var(--gold-pale)',
  borderBottom: '0.5px solid var(--gray-l)',
  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
}
const colheadT = {
  fontSize: 'var(--fs-label)', letterSpacing: '.06em', textTransform: 'uppercase',
  color: 'var(--text-muted)', fontWeight: 500, fontFamily: MONO,
}
const colheadN = { fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }
const btn = {
  border: '0.5px solid var(--gray-l)', background: 'var(--white)', color: 'var(--text-main)',
  borderRadius: 6, padding: '6px 12px', fontFamily: MONO, fontSize: 'var(--fs-body)',
  cursor: 'pointer', whiteSpace: 'nowrap',
}
const btnSm = { ...btn, padding: '4px 11px', fontSize: 'var(--fs-caption)' }

export default function CatalegPeces() {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const tenant = useAuthStore(s => s.tenant)     // la CASA: {nom, codi_tenant, tipologia}
  const canEdit = !!me?.capabilities?.includes('configure')

  const grups = useGarmentGroups()
  const [families, setFamilies] = useState([])
  const [items, setItems] = useState([])
  const [pomsPerGrup, setPomsPerGrup] = useState({})
  const [pomsPerFamilia, setPomsPerFamilia] = useState({})
  const [acumulat, setAcumulat] = useState({})       // itemId → {grup, familia, item, total}

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [nonce, setNonce] = useState(0)

  const [grupSel, setGrupSel] = useState(null)       // codi del grup
  const [famSel, setFamSel] = useState(null)         // id de la família
  const [cercaGrup, setCercaGrup] = useState('')
  const [cercaFam, setCercaFam] = useState('')
  const [modal, setModal] = useState(null)

  // Les tres poblacions en UNA passada cadascuna. Els recomptes de POMs de grup i de família es
  // demanen SENCERS i s'agrupen aquí: filtrar-los per àncora seria una crida per fila de columna.
  useEffect(() => {
    let viu = true
    setLoading(true); setError(false)
    Promise.all([
      garmentTypes.list({ ordering: 'codi_client', page_size: 500 }),
      garmentTypeItems.list({ page_size: 1000 }),
      garmentGroupPomMaps.list({ page_size: 2000 }),
      garmentTypePomMaps.list({ page_size: 2000 }),
    ]).then(([fRes, iRes, gpRes, fpRes]) => {
      if (!viu) return
      const llista = (r) => r.data?.results ?? (Array.isArray(r.data) ? r.data : [])
      setFamilies(llista(fRes))
      setItems(llista(iRes))
      const compta = (files, clau) => files.reduce((acc, m) => {
        acc[m[clau]] = (acc[m[clau]] || 0) + 1
        return acc
      }, {})
      setPomsPerGrup(compta(llista(gpRes), 'garment_group'))
      setPomsPerFamilia(compta(llista(fpRes), 'garment_type'))
    }).catch(() => { if (viu) setError(true) })
      .finally(() => { if (viu) setLoading(false) })
    return () => { viu = false }
  }, [nonce])

  // La selecció es DERIVA, no se sincronitza amb efectes: mentre l'usuari no ha triat res val el
  // primer grup amb famílies (com la maqueta en obrir-se) i la primera família del grup. Fer-ho
  // amb `useEffect` + `setState` costaria un render en cascada a cada càrrega i deixaria un
  // instant amb la columna 3 apuntant a una família d'un altre grup.
  const grupEfectiu = useMemo(() => {
    if (grupSel && grups.some(g => g.codi === grupSel)) return grupSel
    return grups.find(g => families.some(f => f.grup === g.codi))?.codi ?? null
  }, [grupSel, grups, families])

  const famsDelGrup = useMemo(
    () => families.filter(f => f.grup === grupEfectiu), [families, grupEfectiu])

  const famEfectiva = useMemo(() => {
    if (famSel != null && famsDelGrup.some(f => f.id === famSel)) return famSel
    return famsDelGrup[0]?.id ?? null
  }, [famSel, famsDelGrup])

  const itemsDeFam = useMemo(
    () => items.filter(it => it.garment_type === famEfectiva), [items, famEfectiva])

  // L'acumulació i les extensions de fitxer són per ITEM: una crida per fila VISIBLE, i només
  // per a les visibles (una família en porta poques). Es memoritzen per id perquè tornar a una
  // família ja vista no les torni a demanar.
  //
  // Les extensions són l'única manera d'omplir la columna «Fitxers» tal com la v4 la pinta
  // («N · JPG · AI · DXF»): `ItemFitxer.tipus` NO és l'extensió sinó un vocabulari de ROL
  // (SKETCH_SVG, PATRO, RUL…), i el compte que el serializer ja anota és només la N.
  useEffect(() => {
    let viu = true
    const pendents = itemsDeFam.filter(it => !(it.id in acumulat))
    if (pendents.length === 0) return undefined
    Promise.all(pendents.map(it => Promise.all([
      garmentTypeItems.acumulacio(it.id).then(r => r.data?.recompte || null).catch(() => null),
      itemFitxers.list({ garment_type_item: it.id, is_current: true, page_size: 200 })
        .then(r => r.data?.results ?? (Array.isArray(r.data) ? r.data : [])).catch(() => []),
    ]).then(([recompte, fitxers]) => [it.id, { recompte, exts: extensionsDe(fitxers) }])))
      .then(parells => {
        if (viu) setAcumulat(prev => ({ ...prev, ...Object.fromEntries(parells) }))
      })
    return () => { viu = false }
  }, [itemsDeFam, acumulat])

  const recarrega = useCallback(() => { setAcumulat({}); setNonce(n => n + 1) }, [])

  const grupsMostrats = useMemo(() => {
    const q = cercaGrup.trim().toLowerCase()
    if (!q) return grups
    return grups.filter(g => `${nomLocal(g, lang)} ${g.codi}`.toLowerCase().includes(q))
  }, [grups, cercaGrup, lang])

  const famsMostrades = useMemo(() => {
    const q = cercaFam.trim().toLowerCase()
    if (!q) return famsDelGrup
    return famsDelGrup.filter(f => `${f.nom_client || ''} ${f.codi_client || ''}`
      .toLowerCase().includes(q))
  }, [famsDelGrup, cercaFam])

  const grupObj = grups.find(g => g.codi === grupEfectiu) || null
  const famObj = families.find(f => f.id === famEfectiva) || null

  if (loading) return <Center>{t('cataleg_peces.loading')}</Center>
  if (error) return <Center>{t('cataleg_peces.load_error')}</Center>

  return (
    <div style={{ minWidth: 0, maxWidth: 1600 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', marginBottom: 8, fontFamily: MONO }}>
        {t('cataleg_peces.crumb_config')} › <b style={{ color: 'var(--text-main)' }}>{t('cataleg_peces.title')}</b>
      </div>
      <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 600, margin: '0 0 3px', fontFamily: MONO }}>
        {t('cataleg_peces.title')}
        {tenant?.nom && (
          <span style={{
            background: 'var(--gold)', color: 'var(--white)', borderRadius: 999,
            padding: '2px 11px', fontSize: 'var(--fs-caption)', marginLeft: 10, fontWeight: 400,
          }}>{tenant.nom}</span>
        )}
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', margin: '0 0 14px', lineHeight: 1.65, fontFamily: MONO }}>
        {t('cataleg_peces.subtitle')}
      </p>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div style={{ display: 'grid', gridTemplateColumns: '222px 222px 1fr', gap: 13, alignItems: 'start' }}>
        {/* ── 1 · GRUP ── */}
        <div style={panel}>
          <div style={colhead}>
            <span style={colheadT}>{t('cataleg_peces.col_group')}</span>
            <span style={colheadN}>{grups.length}</span>
          </div>
          <div style={{ padding: '8px 11px', borderBottom: '0.5px solid var(--gray-l)' }}>
            <input value={cercaGrup} onChange={e => setCercaGrup(e.target.value)}
              placeholder={t('cataleg_peces.search_group')}
              style={{ ...selS, width: '100%', fontStyle: cercaGrup ? 'normal' : 'italic' }} />
          </div>
          <div style={{ maxHeight: 520, overflowY: 'auto' }}>
            {grupsMostrats.map(g => (
              <FilaCascada
                key={g.codi}
                nom={nomLocal(g, lang)}
                codi={g.codi}
                actiu={g.codi === grupEfectiu}
                dreta={<>
                  <div style={ct}>{t('cataleg_peces.n_fam', { count: families.filter(f => f.grup === g.codi).length })}</div>
                  <div style={pm}>{t('cataleg_peces.n_poms', { count: pomsPerGrup[g.id] || 0 })}</div>
                </>}
                onClick={() => { setGrupSel(g.codi); setFamSel(null) }}
              />
            ))}
          </div>
          {canEdit && (
            <div style={addrow}>
              <button style={{ ...btn, width: '100%', textAlign: 'center' }}
                onClick={() => setModal({ tipus: 'grup' })}>{t('cataleg_peces.new_group')}</button>
            </div>
          )}
        </div>

        {/* ── 2 · FAMÍLIA ── */}
        <div style={panel}>
          <div style={colhead}>
            <span style={colheadT}>{t('cataleg_peces.col_family')}</span>
            <span style={colheadN}>{grupEfectiu ? famsDelGrup.length : '—'}</span>
          </div>
          <div style={{ padding: '8px 11px', borderBottom: '0.5px solid var(--gray-l)' }}>
            <input value={cercaFam} onChange={e => setCercaFam(e.target.value)}
              placeholder={t('cataleg_peces.search_family')}
              style={{ ...selS, width: '100%', fontStyle: cercaFam ? 'normal' : 'italic' }} />
          </div>
          <div style={{ maxHeight: 520, overflowY: 'auto' }}>
            {famsMostrades.map(f => (
              <FilaCascada
                key={f.id}
                nom={f.nom_client || f.nom_ca || f.codi_client}
                codi={f.codi_client}
                actiu={f.id === famEfectiva}
                dreta={<>
                  <div style={ct}>{t('cataleg_peces.n_items', { count: f.items_count ?? 0 })}</div>
                  <div style={pm}>{t('cataleg_peces.plus_n_poms', { count: pomsPerFamilia[f.id] || 0 })}</div>
                </>}
                onClick={() => setFamSel(f.id)}
              />
            ))}
          </div>
          {canEdit && (
            <div style={addrow}>
              <button style={{ ...btn, width: '100%', textAlign: 'center' }}
                onClick={() => setModal({ tipus: 'familia' })}>{t('cataleg_peces.new_family')}</button>
            </div>
          )}
        </div>

        {/* ── 3 · ITEM ── */}
        <div style={panel}>
          <div style={colhead}>
            <span style={colheadT}>
              {t('cataleg_peces.col_item')}
              <span style={{ textTransform: 'none', letterSpacing: 0, color: 'var(--gray)' }}>
                {' '}{t('cataleg_peces.col_item_note')}
              </span>
            </span>
            <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={colheadN}>
                {famEfectiva ? t('cataleg_peces.items_count', { count: itemsDeFam.length }) : '—'}
              </span>
              {canEdit && famEfectiva && (
                <button style={btnSm} onClick={() => setModal({ tipus: 'item' })}>
                  {t('cataleg_peces.new_item')}
                </button>
              )}
            </span>
          </div>
          <div style={{
            display: 'grid', gridTemplateColumns: COLS, gap: 12, padding: '7px 14px',
            background: 'var(--gold-pale)', borderBottom: '0.5px solid var(--gray-l)',
          }}>
            {['h_item', 'h_poms_proposed', 'h_run', 'h_base_size', 'h_files'].map(k => (
              <span key={k} style={{
                fontSize: 'var(--fs-label)', letterSpacing: '.05em', textTransform: 'uppercase',
                color: 'var(--text-muted)', fontFamily: MONO,
              }}>{t(`cataleg_peces.${k}`)}</span>
            ))}
            <span />
          </div>
          {itemsDeFam.map(it => (
            <FilaItem key={it.id} it={it} t={t}
              recompte={acumulat[it.id]?.recompte} exts={acumulat[it.id]?.exts}
              onEdit={() => navigate(`/cataleg-peces/items/${it.id}`)} />
          ))}
        </div>
      </div>

      {modal && (
        <ModalAlta tipus={modal.tipus} t={t} grup={grupObj} familia={famObj}
          onCancel={() => setModal(null)}
          onSaved={(msg) => {
            setModal(null); recarrega()
            setFeedback({ type: 'ok', text: msg })
          }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

const addrow = {
  padding: '9px 13px', borderTop: '0.5px solid var(--gray-l)', background: 'var(--bg-muted)',
}
const ct = { fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: MONO }
const pm = { fontSize: 'var(--fs-label)', color: 'var(--gold)', fontFamily: MONO, marginTop: 2 }

// La fila de les columnes 1 i 2: nom + codi a l'esquerra, dos comptadors a la dreta. L'estat
// seleccionat és el de la maqueta: fons pàl·lid i barra d'or a l'esquerra.
function FilaCascada({ nom, codi, actiu, dreta, onClick }) {
  return (
    <button type="button" onClick={onClick} style={{
      display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8,
      width: '100%', textAlign: 'left', padding: '9px 13px', cursor: 'pointer', border: 'none',
      borderBottom: '0.5px solid var(--gray-l)', fontFamily: MONO,
      background: actiu ? 'var(--gold-pale)' : 'transparent',
      boxShadow: actiu ? 'inset 3px 0 0 var(--gold)' : 'none',
    }}>
      <span style={{ minWidth: 0 }}>
        <span style={{
          display: 'block', fontSize: 'var(--fs-body)', lineHeight: 1.35,
          color: actiu ? 'var(--gold)' : 'var(--text-main)', fontWeight: actiu ? 600 : 400,
        }}>{nom}</span>
        <span style={{
          display: 'block', fontSize: 'var(--fs-label)', color: 'var(--gray)',
          letterSpacing: '.04em', marginTop: 2,
        }}>{codi}</span>
      </span>
      <span style={{ textAlign: 'right', whiteSpace: 'nowrap', flex: 'none' }}>{dreta}</span>
    </button>
  )
}

// La LÍNIA d'item: sis columnes sempre a la mateixa posició. És el que la v4 canvia respecte de
// la v3 («els items són línies, no pastilles»): es comparen d'un cop d'ull i no hi ha scroll
// lateral. Un sol botó, «Editar» — res més a la línia.
// L'extensió surt del NOM del fitxer, no de `tipus`: `ItemFitxer.tipus` és un vocabulari de rol
// (ALTRES · DOCUMENT · TECHSHEET · EXPORT · PATRO · ESCALAT · SKETCH_* · MARCADA · RUL) i només
// «RUL» hi coincideix. Sense duplicats i en l'ordre en què apareixen.
function extensionsDe(fitxers) {
  const vistes = []
  for (const f of fitxers) {
    const nom = f.nom_fitxer || ''
    const punt = nom.lastIndexOf('.')
    if (punt < 0 || punt === nom.length - 1) continue
    const ext = nom.slice(punt + 1).toUpperCase()
    if (!vistes.includes(ext)) vistes.push(ext)
  }
  return vistes
}

function FilaItem({ it, t, recompte, exts, onEdit }) {
  const g = recompte?.grup ?? 0
  const f = recompte?.familia ?? 0
  const p = recompte?.item ?? 0
  const tot = recompte?.total ?? 0
  const w = (x) => (tot ? Math.round((x / tot) * 100) : 0)

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: COLS, gap: 12, alignItems: 'center',
      padding: '11px 14px', borderBottom: '0.5px solid var(--gray-l)', fontFamily: MONO,
    }}>
      <span>
        <span style={{ display: 'block', fontSize: 'var(--fs-body)', fontWeight: 600 }}>{it.name}</span>
        <span style={{
          display: 'block', fontSize: 'var(--fs-label)', color: 'var(--gray)',
          letterSpacing: '.04em', marginTop: 2,
        }}>{it.code}</span>
      </span>

      <span>
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
          {t('cataleg_peces.acc_group')} <b style={{ color: 'var(--text-main)' }}>{g}</b>
          {' · '}{t('cataleg_peces.acc_family')} <b style={{ color: 'var(--text-main)' }}>{f}</b>
          {' · '}{t('cataleg_peces.acc_item')} <b style={{ color: 'var(--text-main)' }}>{p}</b>
          <span style={{ color: 'var(--gold)', fontWeight: 600, fontSize: 'var(--fs-body)', marginLeft: 5 }}>{tot}</span>
        </span>
        <span style={{
          display: 'flex', height: 5, borderRadius: 3, overflow: 'hidden', marginTop: 5,
          background: 'var(--gray-l)',
        }}>
          <i style={{ display: 'block', width: `${w(g)}%`, background: 'var(--gold-l)' }} />
          <i style={{ display: 'block', width: `${w(f)}%`, background: 'var(--gold-border)' }} />
          <i style={{ display: 'block', width: `${w(p)}%`, background: 'var(--gold)' }} />
        </span>
      </span>

      <span style={valorFila}>{it.proposed_size_system_nom || '—'}</span>
      <span style={valorFila}>{it.proposed_base_size_label || '—'}</span>
      <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
        <b style={{ color: 'var(--text-main)' }}>{it.fitxers_count ?? 0}</b>
        {' · '}{exts?.length ? exts.join(' · ') : '—'}
      </span>

      <span style={{ textAlign: 'right' }}>
        <button style={btnSm} onClick={onEdit}>{t('cataleg_peces.edit')}</button>
      </span>
    </div>
  )
}

const valorFila = { fontSize: 'var(--fs-body)', fontWeight: 600 }

// Les tres altes de la maqueta («＋ Nou grup» · «＋ Nova família» · «＋ Nou item»). Un sol modal:
// els tres formularis són el mateix parell codi+nom, i el que canvia és a què pengen.
function ModalAlta({ tipus, t, grup, familia, onCancel, onSaved, onError }) {
  const [codi, setCodi] = useState('')
  const [nom, setNom] = useState('')
  const [desant, setDesant] = useState(false)
  const invalid = !codi.trim() || !nom.trim()
  const titol = { grup: 'new_group', familia: 'new_family', item: 'new_item' }[tipus]

  const desa = () => {
    if (invalid) return
    setDesant(true)
    const c = codi.trim(); const n = nom.trim()
    const crida = tipus === 'grup'
      ? garmentGroups.create({ codi: c, nom: n })
      : tipus === 'familia'
        ? garmentTypes.create({ codi_client: c, nom_client: n, grup: grup?.codi || '', grup_ref: grup?.id ?? null })
        : garmentTypeItems.create({ garment_type: familia?.id, code: c, name: n })
    crida
      .then(() => onSaved(t('cataleg_peces.saved')))
      .catch(e => onError(
        e?.response?.data?.codi?.[0] || e?.response?.data?.codi_client?.[0]
        || e?.response?.data?.code?.[0] || e?.response?.data?.detail
        || t('cataleg_peces.save_error')))
      .finally(() => setDesant(false))
  }

  return (
    <Modal title={t(`cataleg_peces.${titol}`)}
      cancelLabel={t('cataleg_peces.back')} confirmLabel={t('cataleg_peces.save')}
      onCancel={onCancel} onConfirm={desa} confirmDisabled={desant || invalid}>
      <div style={{ marginBottom: 12 }}>
        <label style={etiqueta}>{t('cataleg_peces.f_code')}</label>
        <input value={codi} onChange={e => setCodi(e.target.value)} style={{ ...selS, width: '100%' }} />
      </div>
      <div>
        <label style={etiqueta}>{t('cataleg_peces.f_name')}</label>
        <input value={nom} onChange={e => setNom(e.target.value)} style={{ ...selS, width: '100%' }} />
      </div>
    </Modal>
  )
}

const etiqueta = {
  fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)',
  textTransform: 'uppercase', display: 'block', marginBottom: 6,
}
