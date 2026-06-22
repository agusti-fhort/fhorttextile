import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  garmentTypeItems, gradingRuleSets, garmentGroups, sizeDefinitions,
} from '../api/endpoints'
import AxesSelector from '../components/grading/AxesSelector'
import RuleSetPicker from '../components/grading/RuleSetPicker'
import MeasurementBaseGrid from '../components/MeasurementBaseGrid/MeasurementBaseGrid'

// ItemAuthoring — pàgina d'autoria d'Item full-screen (Sprint Llibreria d'Items, B3). Wizard de
// 4 passos que reutilitza components existents: AxesSelector (1) → RuleSetPicker (2, assigna la FK
// grading_rule_set via serializer de B3a) → selector de talla base (3, validat pel clean d'A3) →
// MeasurementBaseGrid (4). Serveix CREAR (des de /nou/:typeId) i OBRIR-existent (/:itemId/editar).
// Substitueix l'ItemModal de GarmentTypes (code/name/complexity hi viuen ara, al pas 1).

const MONO = 'IBM Plex Mono, monospace'
const STEPS = ['step1_axes', 'step2_ruleset', 'step3_basesize', 'step4_grid']

const btnPrimary = (disabled) => ({
  background: disabled ? '#ccc' : 'var(--gold)', color: 'var(--white)', border: 'none',
  borderRadius: 6, padding: '8px 20px', fontSize: 'var(--fs-body)', fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)', border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '8px 16px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}
const inputS = {
  width: '100%', border: '0.5px solid var(--border)', borderRadius: 6, padding: '8px 10px',
  fontSize: 'var(--fs-body)', boxSizing: 'border-box', background: 'var(--white)',
}

export default function ItemAuthoring() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { typeId, itemId: routeItemId } = useParams()
  const isEdit = !!routeItemId

  const [itemId, setItemId] = useState(routeItemId || null)   // es fixa en crear
  const [step, setStep] = useState(1)

  // Identitat de l'item (pas 1, abans la vivia ItemModal).
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [order, setOrder] = useState(0)
  const [active, setActive] = useState(true)

  // Dades de grading (carregades un cop) + selecció.
  const [ruleSets, setRuleSets] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [axes, setAxes] = useState({ target: null, construction: null, fit: null, garmentGroup: null })
  const [chosenRulesetId, setChosenRulesetId] = useState(null)

  // Talla base (pas 3).
  const [sizeDefs, setSizeDefs] = useState([])
  const [baseSizeId, setBaseSizeId] = useState(null)

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const chosenRuleset = useMemo(
    () => ruleSets.find(r => r.id === chosenRulesetId) || null,
    [ruleSets, chosenRulesetId],
  )

  // ── Càrrega inicial: rulesets + garment-groups (id→codi) + item (si edició) ──
  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([
      gradingRuleSets.list({ page_size: 200 }),
      garmentGroups.list({ page_size: 200 }),
      isEdit ? garmentTypeItems.get(routeItemId) : Promise.resolve(null),
    ]).then(([rsRes, ggRes, itRes]) => {
      if (!alive) return
      const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
      const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
      const map = {}; gg.forEach(g => { map[g.id] = g.codi })
      setRuleSets(rs); setGgCodiById(map)
      if (itRes?.data) {
        const it = itRes.data
        setCode(it.code || ''); setName(it.name || '')
        setOrder(it.complexity_order ?? 0); setActive(it.active ?? true)
        setChosenRulesetId(it.grading_rule_set ?? null)
        setBaseSizeId(it.base_size_definition ?? null)
        // Deriva els eixos del ruleset assignat (millor esforç; garment_group pot ser null).
        const rsObj = rs.find(r => r.id === it.grading_rule_set)
        if (rsObj) {
          setAxes({
            target: rsObj.targets_codis?.[0] ?? null,
            construction: rsObj.construction_codi ?? null,
            fit: rsObj.fit_type_codi ?? null,
            garmentGroup: rsObj.garment_group ? (map[rsObj.garment_group] ?? null) : null,
          })
        }
      }
    }).catch(() => { if (alive) setError(t('item_authoring.load_error')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [isEdit, routeItemId, t])

  // ── Talla base: carrega les SizeDefinitions del size_system del ruleset triat ──
  const loadSizeDefs = useCallback((sizeSystemId) => {
    if (!sizeSystemId) { setSizeDefs([]); return }
    sizeDefinitions.list({ size_system: sizeSystemId, ordering: 'ordre', page_size: 200 })
      .then(res => setSizeDefs(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setSizeDefs([]))
  }, [])

  useEffect(() => {
    if (chosenRuleset?.size_system) loadSizeDefs(chosenRuleset.size_system)
    else setSizeDefs([])
  }, [chosenRuleset, loadSizeDefs])

  const identityValid = (isEdit || code.trim()) && name.trim()
  const axesComplete = axes.target && axes.construction && axes.fit && axes.garmentGroup

  // ── Pas 1 → 2: assegura que l'item existeix (crea o desa identitat) ──
  const ensureItemAndAdvance = async () => {
    setBusy(true); setError(null)
    try {
      const payload = {
        name: name.trim(), complexity_order: Number(order) || 0, active,
      }
      if (itemId) {
        await garmentTypeItems.update(itemId, payload)
      } else {
        const res = await garmentTypeItems.create({
          garment_type: Number(typeId), code: code.trim(), ...payload,
        })
        setItemId(res.data.id)
      }
      setStep(2)
    } catch (e) {
      setError(e?.response?.data?.code?.[0] || e?.response?.data?.detail || t('item_authoring.save_error'))
    } finally {
      setBusy(false)
    }
  }

  // ── Pas 2: assignar ruleset (FK via serializer B3a). Si canvia de size_system, neteja talla base. ──
  const assignRuleset = async (rs) => {
    setBusy(true); setError(null)
    try {
      const payload = { grading_rule_set: rs.id }
      const incompatible = baseSizeId && chosenRuleset && chosenRuleset.size_system !== rs.size_system
      if (incompatible) payload.base_size_definition = null
      await garmentTypeItems.update(itemId, payload)
      setChosenRulesetId(rs.id)
      if (incompatible) setBaseSizeId(null)
    } catch (e) {
      setError(e?.response?.data?.base_size_definition?.[0] || e?.response?.data?.detail || t('item_authoring.save_error'))
    } finally {
      setBusy(false)
    }
  }

  // ── Pas 3: triar talla base (clean d'A3 valida al backend) ──
  const pickBaseSize = async (sd) => {
    setBusy(true); setError(null)
    try {
      await garmentTypeItems.update(itemId, { base_size_definition: sd.id })
      setBaseSizeId(sd.id)
    } catch (e) {
      setError(e?.response?.data?.base_size_definition?.[0] || t('item_authoring.save_error'))
    } finally {
      setBusy(false)
    }
  }

  const canNext =
    step === 1 ? (identityValid && axesComplete) :
    step === 2 ? !!chosenRulesetId :
    step === 3 ? !!baseSizeId : false

  const goNext = () => {
    if (step === 1) return ensureItemAndAdvance()
    setStep(s => Math.min(4, s + 1))
  }
  const goBack = () => (step === 1 ? navigate('/garment-types') : setStep(s => s - 1))
  const finish = () => navigate('/garment-types')

  if (loading) {
    return <div style={{ padding: 40, color: 'var(--text-muted)', fontFamily: MONO }}>{t('common.loading')}</div>
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', padding: '24px 32px', fontFamily: 'IBM Plex Sans, sans-serif' }}>
      {/* Capçalera */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, maxWidth: 1100, marginInline: 'auto' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO }}>
          {isEdit ? t('item_authoring.title_edit', { code }) : t('item_authoring.title_new')}
        </h1>
        <button type="button" onClick={() => navigate('/garment-types')} style={btnSecondary}>
          ✕ {t('item_authoring.close')}
        </button>
      </div>

      {/* Stepper */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, maxWidth: 1100, marginInline: 'auto', flexWrap: 'wrap' }}>
        {STEPS.map((key, i) => {
          const n = i + 1
          const done = n < step
          const cur = n === step
          return (
            <div key={key} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 6,
              background: cur ? '#fdf6ee' : 'transparent',
              border: `1px solid ${cur ? 'var(--gold)' : 'var(--border)'}`,
              opacity: done || cur ? 1 : 0.55,
            }}>
              <span style={{
                width: 20, height: 20, borderRadius: '50%', display: 'inline-flex',
                alignItems: 'center', justifyContent: 'center', fontSize: 'var(--fs-caption)',
                fontWeight: 700, color: 'var(--white)',
                background: cur || done ? 'var(--gold)' : 'var(--text-muted)',
              }}>{done ? '✓' : n}</span>
              <span style={{ fontSize: 'var(--fs-body)', fontWeight: cur ? 600 : 400 }}>
                {t(`item_authoring.${key}`)}
              </span>
            </div>
          )
        })}
      </div>

      <div style={{ maxWidth: 1100, marginInline: 'auto' }}>
        {error && (
          <div style={{
            background: '#fdecea', border: '1px solid #f5c6cb', borderRadius: 8,
            padding: '8px 14px', marginBottom: 16, fontSize: 'var(--fs-body)', color: '#a12622',
          }}>{error}</div>
        )}

        {/* PAS 1: identitat + eixos */}
        {step === 1 && (
          <div>
            <div style={{
              border: '0.5px solid var(--border)', borderRadius: 12, background: 'var(--white)',
              padding: 18, marginBottom: 20,
            }}>
              <p style={sectionTitle}>{t('item_authoring.identity')}</p>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <Field label={t('item_authoring.f_code')} style={{ flex: '1 1 160px' }}>
                  <input value={code} disabled={isEdit} onChange={e => setCode(e.target.value)}
                    placeholder="chino" style={{ ...inputS, opacity: isEdit ? 0.6 : 1 }} />
                </Field>
                <Field label={t('item_authoring.f_name')} style={{ flex: '2 1 220px' }}>
                  <input value={name} onChange={e => setName(e.target.value)} style={inputS} />
                </Field>
                <Field label={t('item_authoring.f_order')} style={{ flex: '0 1 110px' }}>
                  <input type="number" value={order} onChange={e => setOrder(e.target.value)} style={inputS} />
                </Field>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 8 }}>
                <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />
                <span>{t('item_authoring.active')}</span>
              </label>
            </div>
            <AxesSelector ruleSets={ruleSets} value={axes} onChange={setAxes} />
          </div>
        )}

        {/* PAS 2: triar ruleset */}
        {step === 2 && (
          <div>
            <p style={sectionTitle}>{t('item_authoring.pick_ruleset')}</p>
            <RuleSetPicker
              ruleSets={ruleSets}
              garmentGroupCodiById={ggCodiById}
              axes={axes}
              selectedId={chosenRulesetId}
              actionLabel={t('item_authoring.assign')}
              onPick={assignRuleset}
              onEmptyAction={() => navigate('/poms/grading')}
              emptyActionLabel={t('item_authoring.create_ruleset')}
            />
          </div>
        )}

        {/* PAS 3: talla base */}
        {step === 3 && (
          <div>
            <p style={sectionTitle}>{t('item_authoring.confirm_basesize')}</p>
            {chosenRuleset && (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
                {t('item_authoring.basesize_from', { system: chosenRuleset.size_system_nom || '' })}
              </p>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {sizeDefs.map(sd => (
                <button key={sd.id} type="button" disabled={busy} onClick={() => pickBaseSize(sd)}
                  style={{
                    border: `1px solid ${sd.id === baseSizeId ? 'var(--gold)' : 'var(--border)'}`,
                    borderRadius: 8, padding: '8px 16px', cursor: busy ? 'wait' : 'pointer',
                    background: sd.id === baseSizeId ? '#fdf6ee' : 'var(--white)',
                    color: sd.id === baseSizeId ? 'var(--gold)' : 'var(--text-main)',
                    fontWeight: sd.id === baseSizeId ? 600 : 400, fontFamily: MONO,
                    fontSize: 'var(--fs-body)',
                  }}>
                  {sd.id === baseSizeId ? '★ ' : ''}{sd.etiqueta}
                </button>
              ))}
              {sizeDefs.length === 0 && (
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
                  {t('item_authoring.basesize_none')}
                </span>
              )}
            </div>
          </div>
        )}

        {/* PAS 4: graella de mesures base */}
        {step === 4 && (
          <div>
            <p style={sectionTitle}>{t('item_authoring.measurements')}</p>
            <MeasurementBaseGrid garmentTypeItemId={itemId} />
          </div>
        )}

        {/* Navegació */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 28, paddingTop: 16, borderTop: '0.5px solid var(--border)' }}>
          <button type="button" onClick={goBack} style={btnSecondary}>
            ← {step === 1 ? t('item_authoring.cancel') : t('item_authoring.back')}
          </button>
          {step < 4 ? (
            <button type="button" onClick={goNext} disabled={!canNext || busy} style={btnPrimary(!canNext || busy)}>
              {busy ? t('common.saving') : `${t('item_authoring.next')} →`}
            </button>
          ) : (
            <button type="button" onClick={finish} style={btnPrimary(false)}>
              ✓ {t('item_authoring.finish')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

const sectionTitle = {
  fontSize: 'var(--fs-label)', fontWeight: 700, color: 'var(--gold)',
  letterSpacing: '0.08em', textTransform: 'uppercase', margin: '0 0 12px',
}

function Field({ label, style, children }) {
  return (
    <div style={{ marginBottom: 4, ...style }}>
      <label style={{
        fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)',
        textTransform: 'uppercase', display: 'block', marginBottom: 6,
      }}>{label}</label>
      {children}
    </div>
  )
}
