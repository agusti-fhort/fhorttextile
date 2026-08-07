import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import {
  garmentTypeItems, garmentTypes, sizeSystems, sizeDefinitions, itemFitxers,
} from '../api/endpoints'
import { UPLOAD_ACCEPT } from '../utils/uploads'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import { selS } from '../components/ui/buttons'
import TaulaPOMsCataleg from '../components/cataleg/TaulaPOMsCataleg'
import { midaLlegible } from '../components/assets/fileMeta'

// U2 · LA PANTALLA DE L'ITEM — dos tabs («Talles i POMs» · «Fitxers») amb el run i la talla base
// fixats a dalt, segons `maqueta_cataleg_peces_v4.html`.
//
// És UNA PANTALLA, no un panell sota la llista: es torna al catàleg pel camí de sempre (el
// molla de pa). Substitueix `ItemAuthoring` (el stepper de 2 passos), que la v4 suprimeix.
//
// El run i la talla base són la PROPOSTA de l'item (U2/R3: `proposed_size_system` +
// `proposed_base_size_label`), no el joc de regles ni cap `ItemBaseSet`. Buit = «sense proposta»,
// dit i no omplert.

const MONO = 'IBM Plex Mono, monospace'

const btn = {
  border: '0.5px solid var(--gray-l)', background: 'var(--white)', color: 'var(--text-main)',
  borderRadius: 6, padding: '6px 12px', fontFamily: MONO, fontSize: 'var(--fs-body)',
  cursor: 'pointer', whiteSpace: 'nowrap',
}
const tabBtn = (actiu) => ({
  border: `0.5px solid ${actiu ? 'var(--gold)' : 'var(--gray-l)'}`,
  background: actiu ? 'var(--gold-pale)' : 'var(--white)',
  color: actiu ? 'var(--gold)' : 'var(--text-muted)',
  fontWeight: actiu ? 600 : 400,
  borderRadius: 6, padding: '5px 15px', fontFamily: MONO, fontSize: 'var(--fs-body)',
  cursor: 'pointer',
})
const etiquetaEix = {
  fontSize: 'var(--fs-label)', letterSpacing: '.06em', textTransform: 'uppercase',
  color: 'var(--text-muted)', display: 'block', fontFamily: MONO,
}

export default function CatalegPecesItem() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { itemId } = useParams()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [item, setItem] = useState(null)
  const [familia, setFamilia] = useState(null)
  const [runs, setRuns] = useState([])
  const [talles, setTalles] = useState({ run: null, files: [] })
  const [tab, setTab] = useState('poms')
  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState(null)
  const [feedback, setFeedback] = useState(null)

  const carrega = useCallback(async () => {
    setCarregant(true); setError(null)
    try {
      const [itRes, ssRes] = await Promise.all([
        garmentTypeItems.get(itemId),
        sizeSystems.list({ page_size: 200 }),
      ])
      const it = itRes.data
      setItem(it)
      setRuns(ssRes.data?.results ?? (Array.isArray(ssRes.data) ? ssRes.data : []))
      if (it?.garment_type) {
        const fRes = await garmentTypes.get(it.garment_type)
        setFamilia(fRes.data)
      }
    } catch {
      setError(t('cataleg_peces.item_no_trobat'))
    } finally {
      setCarregant(false)
    }
  }, [itemId, t])

  useEffect(() => { carrega() }, [carrega])

  // Les talles del run PROPOSAT: són les píndoles de talla base. Sense run proposat no n'hi ha
  // cap —i això es diu, no s'omple amb el primer run del catàleg.
  //
  // El resultat va LLIGAT al run que el va demanar (el patró de `useLlista`): així no s'ensenyen
  // mai les talles del run anterior, i l'efecte no ha de cridar `setState` de manera síncrona
  // per netejar-les.
  const runProposat = item?.proposed_size_system ?? null
  useEffect(() => {
    if (!runProposat) return undefined
    let viu = true
    sizeDefinitions.list({ size_system: runProposat, ordering: 'ordre', page_size: 200 })
      .then(r => {
        if (viu) setTalles({ run: runProposat, files: r.data?.results ?? (Array.isArray(r.data) ? r.data : []) })
      })
      .catch(() => { if (viu) setTalles({ run: runProposat, files: [] }) })
    return () => { viu = false }
  }, [runProposat])
  const tallesDelRun = talles.run === runProposat ? talles.files : []

  // Canviar de run és tornar a triar la talla base: els dos camps viatgen JUNTS (el backend ho
  // exigeix, i és el que fa la mateixa maqueta). L'etiqueta vella no sobreviu al canvi de run.
  const desaProposta = async (camps) => {
    try {
      const r = await garmentTypeItems.update(itemId, camps)
      setItem(r.data)
    } catch (e) {
      setFeedback({ type: 'err', text: e?.response?.data?.proposed_base_size_label?.[0]
        || e?.response?.data?.detail || t('cataleg_peces.save_error') })
    }
  }

  const canviaRun = (valor) => desaProposta({
    proposed_size_system: valor ? Number(valor) : null,
    proposed_base_size_label: '',
  })

  const triaTalla = (etiqueta) => desaProposta({
    proposed_size_system: item.proposed_size_system,
    proposed_base_size_label: etiqueta,
  })

  if (carregant) return <Center>{t('cataleg_peces.loading')}</Center>
  if (error) return <Center>{error}</Center>
  if (!item) return <Center>{t('cataleg_peces.item_no_trobat')}</Center>

  return (
    <div style={{ minWidth: 0, maxWidth: 1600 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', marginBottom: 8, fontFamily: MONO }}>
        <button type="button" onClick={() => navigate('/cataleg-peces')} style={{
          background: 'none', border: 'none', color: 'var(--gold)', cursor: 'pointer',
          padding: 0, fontFamily: MONO, fontSize: 'var(--fs-caption)',
        }}>{t('cataleg_peces.back_to_catalog')}</button>
        {' › '}<b style={{ color: 'var(--text-main)' }}>{familia?.nom_client || familia?.codi_client || '—'}</b>
        {' › '}<b style={{ color: 'var(--text-main)' }}>{item.name}</b>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div style={{
        background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 9,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '11px 14px', background: 'var(--gold-pale)',
          borderBottom: '0.5px solid var(--gray-l)',
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, fontFamily: MONO }}>{item.name}</span>
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: MONO }}>{item.code}</span>
          <span style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>
            <button style={tabBtn(tab === 'poms')} onClick={() => setTab('poms')}>
              {t('cataleg_peces.tab_sizes_poms')}
            </button>
            <button style={tabBtn(tab === 'fitxers')} onClick={() => setTab('fitxers')}>
              {t('cataleg_peces.tab_files')}
            </button>
          </span>
        </div>

        {tab === 'poms' ? (
          <div>
            <div style={{
              padding: '10px 14px', borderBottom: '0.5px solid var(--gray-l)',
              background: 'var(--bg-muted)',
              display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
            }}>
              <span>
                <span style={etiquetaEix}>{t('cataleg_peces.run_label')}</span>
                <select value={item.proposed_size_system ?? ''} disabled={!canEdit}
                  onChange={e => canviaRun(e.target.value)}
                  style={{ ...selS, minWidth: 220, marginTop: 3 }}>
                  <option value="">{t('cataleg_peces.no_run')}</option>
                  {runs.map(r => <option key={r.id} value={r.id}>{r.nom}</option>)}
                </select>
              </span>
              <span>
                <span style={etiquetaEix}>{t('cataleg_peces.base_size_label')}</span>
                <span style={{ display: 'inline-flex', gap: 5, flexWrap: 'wrap', marginTop: 3 }}>
                  {tallesDelRun.length === 0
                    ? <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: MONO }}>
                      {t('cataleg_peces.no_proposal')}
                    </span>
                    : tallesDelRun.map(sd => {
                      const activa = sd.etiqueta === item.proposed_base_size_label
                      return (
                        <button key={sd.id} type="button" disabled={!canEdit}
                          onClick={() => triaTalla(sd.etiqueta)}
                          style={{
                            border: `0.5px solid ${activa ? 'var(--gold)' : 'var(--gray-l)'}`,
                            background: activa ? 'var(--gold-pale)' : 'var(--white)',
                            color: activa ? 'var(--gold)' : 'var(--text-main)',
                            fontWeight: activa ? 600 : 400,
                            boxShadow: activa ? '0 0 0 2px var(--gold-pale)' : 'none',
                            borderRadius: 6, padding: '4px 11px', fontFamily: MONO,
                            fontSize: 'var(--fs-body)', cursor: canEdit ? 'pointer' : 'default',
                          }}>{sd.etiqueta}</button>
                      )
                    })}
                </span>
              </span>
              <span style={{
                fontSize: 'var(--fs-caption)', color: 'var(--gray)', marginLeft: 'auto',
                fontFamily: MONO,
              }}>{t('cataleg_peces.base_hint')}</span>
            </div>

            <TaulaPOMsCataleg
              itemId={Number(itemId)}
              tallaBase={item.proposed_base_size_label}
              onSaved={() => setFeedback({ type: 'ok', text: t('cataleg_peces.saved') })}
              onError={(text) => setFeedback({ type: 'err', text })}
            />
          </div>
        ) : (
          <TabFitxers itemId={itemId} t={t} canEdit={canEdit}
            onError={(text) => setFeedback({ type: 'err', text })}
            onOk={(text) => setFeedback({ type: 'ok', text })} />
        )}
      </div>
    </div>
  )
}

// El tab «Fitxers»: la llista a l'esquerra (badge d'extensió · nom · mida) i el visor a la dreta.
// La llista NO és `FileList`: aquell pinta nom · TIPUS · DATA i ordena per columnes, i la v4 vol
// badge d'extensió · nom · mida i cap data. El que sí que es reutilitza és `midaLlegible`, que és
// la part pura, i els endpoints d'`itemFitxers` sencers.
function TabFitxers({ itemId, t, canEdit, onError, onOk }) {
  const [fitxers, setFitxers] = useState(null)
  const [sel, setSel] = useState(null)
  const [nonce, setNonce] = useState(0)
  const [pujant, setPujant] = useState(false)

  useEffect(() => {
    let viu = true
    itemFitxers.list({ garment_type_item: itemId, is_current: true, ordering: '-data_pujada' })
      .then(r => {
        if (!viu) return
        const files = r.data?.results ?? (Array.isArray(r.data) ? r.data : [])
        setFitxers(files)
        setSel(prev => (files.some(f => f.id === prev) ? prev : files[0]?.id ?? null))
      })
      .catch(() => { if (viu) setFitxers([]) })
    return () => { viu = false }
  }, [itemId, nonce])

  const actual = useMemo(
    () => (fitxers || []).find(f => f.id === sel) || null, [fitxers, sel])
  const ext = extensio(actual?.nom_fitxer)

  const puja = async (file) => {
    if (!file) return
    setPujant(true)
    try {
      const fd = new FormData()
      fd.append('garment_type_item', itemId)
      fd.append('fitxer', file)
      fd.append('nom', file.name)
      await itemFitxers.create(fd)
      setNonce(n => n + 1)
      onOk(t('cataleg_peces.saved'))
    } catch (e) {
      onError(e?.response?.data?.error || t('cataleg_peces.save_error'))
    } finally {
      setPujant(false)
    }
  }

  const esborra = async () => {
    if (!actual) return
    if (!window.confirm(t('cataleg_peces.confirm_delete_file', { nom: actual.nom_fitxer }))) return
    try {
      await itemFitxers.remove(actual.id)
      setSel(null); setNonce(n => n + 1)
      onOk(t('cataleg_peces.saved'))
    } catch {
      onError(t('cataleg_peces.save_error'))
    }
  }

  if (fitxers === null) {
    return <div style={{ padding: 16, color: 'var(--text-muted)', fontFamily: MONO }}>{t('cataleg_peces.loading')}</div>
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr', minHeight: 320 }}>
      <div style={{ borderRight: '0.5px solid var(--gray-l)' }}>
        {fitxers.length === 0
          ? <div style={{ padding: '14px 13px', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 'var(--fs-caption)', fontStyle: 'italic' }}>
            {t('cataleg_peces.files_empty')}
          </div>
          : fitxers.map(f => {
            const actiu = f.id === sel
            return (
              <button key={f.id} type="button" onClick={() => setSel(f.id)} style={{
                display: 'flex', alignItems: 'center', gap: 9, width: '100%', textAlign: 'left',
                padding: '9px 13px', cursor: 'pointer', border: 'none',
                borderBottom: '0.5px solid var(--gray-l)', fontFamily: MONO,
                background: actiu ? 'var(--gold-pale)' : 'transparent',
                boxShadow: actiu ? 'inset 3px 0 0 var(--gold)' : 'none',
              }}>
                <span style={{
                  fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.04em',
                  borderRadius: 4, padding: '2px 6px', background: 'var(--bg-muted)',
                  color: 'var(--gold)', flex: 'none',
                }}>{extensio(f.nom_fitxer) || '—'}</span>
                <span style={{
                  fontSize: 'var(--fs-caption)', flex: 1, overflow: 'hidden',
                  textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{f.nom_fitxer}</span>
                <span style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>
                  {midaLlegible(f.mida_bytes)}
                </span>
              </button>
            )
          })}
      </div>

      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{
          flex: 1, minHeight: 240, border: '0.5px solid var(--gray-l)', borderRadius: 8,
          background: 'repeating-linear-gradient(45deg, var(--bg-muted), var(--bg-muted) 9px, var(--bg-page) 9px, var(--bg-page) 18px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', fontFamily: MONO,
        }}>
          {!actual ? t('cataleg_peces.preview')
            : ext === 'DXF' ? t('cataleg_peces.preview_dxf')
              : ext === 'RUL' ? t('cataleg_peces.preview_rul')
                : t('cataleg_peces.preview_of', { nom: actual.nom_fitxer })}
        </div>
        {actual && (
          <div style={{
            display: 'flex', gap: 14, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            flexWrap: 'wrap', fontFamily: MONO,
          }}>
            <span><b style={{ color: 'var(--text-main)' }}>{actual.nom_fitxer}</b></span>
            <span>{ext || '—'} · {midaLlegible(actual.mida_bytes)}</span>
            <span>{actual.tipus || ''}</span>
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          {canEdit && (
            <label style={{ ...btn, opacity: pujant ? 0.5 : 1, cursor: pujant ? 'default' : 'pointer' }}>
              {t('cataleg_peces.upload_file')}
              <input type="file" hidden disabled={pujant} accept={UPLOAD_ACCEPT}
                onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; puja(f) }} />
            </label>
          )}
          <a href={actual?.download_url || '#'} style={{
            ...btn, textDecoration: 'none', display: 'inline-block',
            pointerEvents: actual?.download_url ? 'auto' : 'none',
            opacity: actual?.download_url ? 1 : 0.5,
          }}>{t('cataleg_peces.download')}</a>
          {canEdit && (
            <button style={{ ...btn, marginLeft: 'auto', color: 'var(--err)', borderColor: 'var(--err)' }}
              disabled={!actual} onClick={esborra}>{t('cataleg_peces.delete')}</button>
          )}
        </div>
      </div>
    </div>
  )
}

function extensio(nom) {
  const s = String(nom || '')
  const punt = s.lastIndexOf('.')
  return punt < 0 || punt === s.length - 1 ? '' : s.slice(punt + 1).toUpperCase()
}
