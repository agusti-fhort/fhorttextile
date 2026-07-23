import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  garmentTypeItems, gradingRuleSets, garmentGroups, sizeDefinitions,
} from '../api/endpoints'
import CascadeSelector from '../components/CascadeSelector/CascadeSelector'
import RuleSetPicker from '../components/grading/RuleSetPicker'
import MeasurementBaseGrid from '../components/MeasurementBaseGrid/MeasurementBaseGrid'

// ItemAuthoring — pàgina d'autoria d'Item (Sprint Llibreria d'Items, B3 + B3-fix). Viu DINS el
// Shell (àrea de contingut). Wizard de 2 passos que RECOMBINA components existents:
//   PAS 1 CONTEXT: identitat (nom; codi auto-slug) + cascada d'eixos (filtre OPCIONAL) +
//     RuleSetPicker eliminatiu (C5), amb «Sense graduació» com a estat legítim.
//   PAS 2 CONSTRUCCIÓ: talla base OPCIONAL (valida amb clean d'A3) + MeasurementBaseGrid (B1).
// Serveix CREAR (/garment-type-items/nou/:typeId) i OBRIR-existent (/:itemId/editar).
//
// COMPLETESA PROGRESSIVA (C1/C2, 2026-07-23) — l'item és una PLANTILLA, i una plantilla es va
// omplint. Fins avui la pàgina exigia assignar un GradingRuleSet per continuar i, pitjor, l'item
// NOMÉS naixia dins d'aquella assignació: sense graduació no hi havia ni item. Ara:
//   · el GRS és opcional i desassignable (C1: el joc de regles s'assigna al MODEL, no a l'item;
//     el que l'item hi deixa és un SUGGERIMENT),
//   · la talla base és opcional (C2: s'informa quan es carreguen mesures dels seus POMs),
//   · els 4 eixos de la cascada són un filtre, no un gate (C4/C5).
// Vegeu docs/diagnosis/DIAGNOSI_GATE_GRS_ITEM_2026-07-23.md.

const MONO = 'IBM Plex Mono, monospace'
const STEPS = ['step1_context', 'step2_construction']
// C5 — el filtre buit és un estat vàlid i de rescat («mostra'ls tots»), no un estat inicial mort.
const CAP_EIX = { target: null, construction: null, fit: null, garmentGroup: null }

// Slug del nom → codi (SlugField max_length=60). Treu accents, no-alfanumèrics → guió.
const slugify = (s) => (s || '').toLowerCase().trim()
  .normalize('NFD').replace(/[̀-ͯ]/g, '')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60)

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
const linkBtn = {
  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
  color: 'var(--gold)', fontSize: 'var(--fs-body)', textDecoration: 'underline',
}
const sectionTitle = {
  fontSize: 'var(--fs-label)', fontWeight: 700, color: 'var(--gold)',
  letterSpacing: '0.08em', textTransform: 'uppercase', margin: '0 0 12px',
}

export default function ItemAuthoring() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { typeId, itemId: routeItemId } = useParams()
  const isEdit = !!routeItemId

  const [itemId, setItemId] = useState(routeItemId || null)   // es fixa en crear
  const [step, setStep] = useState(1)

  const [name, setName] = useState('')
  const [code, setCode] = useState('')          // edició: existent; creació: derivat del nom
  const [active, setActive] = useState(true)

  const [ruleSets, setRuleSets] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [axes, setAxes] = useState(CAP_EIX)
  const [chosenRulesetId, setChosenRulesetId] = useState(null)

  const [sizeDefs, setSizeDefs] = useState([])
  const [baseSizeId, setBaseSizeId] = useState(null)

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const chosenRuleset = useMemo(
    () => ruleSets.find(r => r.id === chosenRulesetId) || null,
    [ruleSets, chosenRulesetId],
  )
  const anyAxis = !!(axes.target || axes.construction || axes.fit || axes.garmentGroup)
  // Codi mostrat: en edició el real (immutable); en creació el slug derivat del nom.
  const shownCode = isEdit ? code : slugify(name)

  // ── Càrrega inicial ──
  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([
      gradingRuleSets.list({ page_size: 200, amb_regles: 1 }),
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
        setCode(it.code || ''); setName(it.name || ''); setActive(it.active ?? true)
        setChosenRulesetId(it.grading_rule_set ?? null)
        setBaseSizeId(it.base_size_definition ?? null)
        const rsObj = rs.find(r => r.id === it.grading_rule_set)
        if (rsObj) setAxes({
          target: rsObj.targets_codis?.[0] ?? null,
          construction: rsObj.construction_codi ?? null,
          fit: rsObj.fit_type_codi ?? null,
          garmentGroup: rsObj.garment_group ? (map[rsObj.garment_group] ?? null) : null,
        })
      }
    }).catch(() => { if (alive) setError(t('item_authoring.load_error')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [isEdit, routeItemId, t])

  // ── Talla base: SizeDefinitions del size_system del ruleset triat ──
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

  // ── L'item neix del NOM, no de la graduació (a1) ──────────────────────────────────────
  // Abans la creació vivia dins d'`assignRuleset`: no triar ruleset volia dir no tenir item.
  // Ara qualsevol acció que necessiti un id el garanteix aquí, i la primera és «Següent».
  const ensureItem = async () => {
    if (itemId) return itemId
    const res = await garmentTypeItems.create({
      garment_type: Number(typeId), code: slugify(name), name: name.trim(), active,
    })
    setItemId(res.data.id); setCode(res.data.code || slugify(name))
    return res.data.id
  }

  // ── Pas 1: assignar ruleset (suggeriment de l'item, mai obligació) ──
  const assignRuleset = async (rs) => {
    if (!name.trim()) { setError(t('item_authoring.need_name')); return }
    setBusy(true); setError(null)
    try {
      const id = await ensureItem()
      const payload = { grading_rule_set: rs.id }
      const incompatible = baseSizeId && chosenRuleset && chosenRuleset.size_system !== rs.size_system
      if (incompatible) payload.base_size_definition = null
      await garmentTypeItems.update(id, payload)
      setChosenRulesetId(rs.id)
      if (incompatible) setBaseSizeId(null)
    } catch (e) {
      setError(e?.response?.data?.code?.[0]
        || e?.response?.data?.base_size_definition?.[0]
        || e?.response?.data?.detail || t('item_authoring.save_error'))
    } finally {
      setBusy(false)
    }
  }

  // ── a3 · «Sense graduació»: el camí de desassignació que no existia ──────────────────────
  // Sense això, el dany d'una assignació era IRREVERSIBLE per UI (§3.3 de la diagnosi).
  // La talla base NO es toca: és patrimoni de l'item, no del ruleset que se'n va.
  const clearRuleset = async () => {
    if (!itemId || chosenRulesetId == null) { setChosenRulesetId(null); return }
    setBusy(true); setError(null)
    try {
      await garmentTypeItems.update(itemId, { grading_rule_set: null })
      setChosenRulesetId(null)
    } catch (e) {
      setError(e?.response?.data?.detail || t('item_authoring.save_error'))
    } finally {
      setBusy(false)
    }
  }

  // ── Pas 2: talla base (clean d'A3 valida al backend) ──
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

  // a2 — l'única condició per continuar és tenir un nom: és l'única cosa que un item NO pot no
  // tenir (el codi se'n deriva). Tota la resta —graduació, talla base, POMs— és progressiva.
  const canNext = step === 1 ? !!name.trim() : false

  const goNext = async () => {
    if (step !== 1) return
    setBusy(true); setError(null)
    try {
      const id = await ensureItem()
      await garmentTypeItems.update(id, { name: name.trim(), active })  // desa nom (codi immutable)
      setStep(2)
    } catch (e) {
      setError(e?.response?.data?.code?.[0]
        || e?.response?.data?.detail || t('item_authoring.save_error'))
    } finally {
      setBusy(false)
    }
  }
  const goBack = () => (step === 1 ? navigate('/garment-types') : setStep(1))
  const finish = () => navigate('/garment-types')

  if (loading) {
    return <div style={{ padding: 32, color: 'var(--text-muted)', fontFamily: MONO }}>{t('common.loading')}</div>
  }

  return (
    <div style={{ minWidth: 0, maxWidth: 1100 }}>
      {/* Capçalera */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>
          {isEdit ? t('item_authoring.title_edit', { code }) : t('item_authoring.title_new')}
        </h1>
        <button type="button" onClick={() => navigate('/garment-types')} style={btnSecondary}>
          ✕ {t('item_authoring.close')}
        </button>
      </div>

      {/* Stepper (2 passos) */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
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

      {error && (
        <div style={{
          background: '#fdecea', border: '1px solid #f5c6cb', borderRadius: 8,
          padding: '8px 14px', marginBottom: 16, fontSize: 'var(--fs-body)', color: '#a12622',
        }}>{error}</div>
      )}

      {/* PAS 1 · CONTEXT */}
      {step === 1 && (
        <div>
          <div style={{
            border: '0.5px solid var(--border)', borderRadius: 12, background: 'var(--white)',
            padding: 18, marginBottom: 20,
          }}>
            <p style={sectionTitle}>{t('item_authoring.identity')}</p>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <div style={{ flex: '2 1 260px' }}>
                <label style={fieldLabel}>{t('item_authoring.f_name')}</label>
                <input value={name} onChange={e => setName(e.target.value)}
                  placeholder={t('item_authoring.name_placeholder')} style={inputS} />
              </div>
              <div style={{ flex: '1 1 180px' }}>
                <label style={fieldLabel}>{t('item_authoring.code_auto_label')}</label>
                <div style={{
                  ...inputS, background: 'var(--bg-muted)', color: 'var(--text-muted)',
                  fontFamily: MONO, minHeight: 19,
                }}>{shownCode || '—'}</div>
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 10 }}>
              <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />
              <span>{t('item_authoring.active')}</span>
            </label>
          </div>

          {/* C4/C5 — els 4 eixos ja no són un gate: acoten la llista i es poden netejar. */}
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <p style={{ ...sectionTitle, marginBottom: 6 }}>{t('item_authoring.filter_optional')}</p>
            {anyAxis && (
              <button type="button" onClick={() => setAxes(CAP_EIX)} style={linkBtn}>
                {t('item_authoring.filter_clear')}
              </button>
            )}
          </div>
          <CascadeSelector mode="single" maxLevel="group" ruleSets={ruleSets} value={axes} onChange={setAxes} />

          <div style={{ marginTop: 8 }}>
            <p style={sectionTitle}>{t('item_authoring.pick_ruleset')}</p>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', margin: '0 0 10px' }}>
              {t('item_authoring.ruleset_optional')}
            </p>
            {/* a3 — «Sense graduació» com a estat triable, no com a absència accidental. */}
            <button type="button" onClick={clearRuleset} disabled={busy}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 12,
                border: `1px solid ${chosenRulesetId == null ? 'var(--gold)' : 'var(--border)'}`,
                background: chosenRulesetId == null ? '#fdf6ee' : 'var(--white)',
                color: chosenRulesetId == null ? 'var(--gold)' : 'var(--text-muted)',
                fontWeight: chosenRulesetId == null ? 600 : 400,
                borderRadius: 8, padding: '8px 16px', fontSize: 'var(--fs-body)',
                cursor: busy ? 'wait' : 'pointer',
              }}>
              <i className="ti ti-circle-off" aria-hidden="true" />
              {chosenRulesetId == null ? t('item_authoring.no_grading_current') : t('item_authoring.no_grading')}
            </button>
            <RuleSetPicker
              ruleSets={ruleSets}
              garmentGroupCodiById={ggCodiById}
              axes={axes}
              eliminatiu
              selectedId={chosenRulesetId}
              actionLabel={t('item_authoring.assign')}
              onPick={assignRuleset}
              onEmptyAction={() => navigate('/poms/grading')}
              emptyActionLabel={t('item_authoring.create_ruleset')}
            />
          </div>

          {/* SLOT D'IMPORT — previst (Fase C), inert. NO construir lògica. */}
          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '0.5px dashed var(--border)' }}>
            <button type="button" disabled title={t('item_authoring.import_tooltip')}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                background: 'transparent', color: 'var(--text-muted)',
                border: '1px dashed var(--border)', borderRadius: 8, padding: '8px 16px',
                fontSize: 'var(--fs-body)', cursor: 'not-allowed', opacity: 0.7,
              }}>
              <i className="ti ti-file-import" />
              {t('item_authoring.import_soon')}
              <span style={{
                fontSize: 'var(--fs-caption)', background: 'var(--bg-muted)', color: 'var(--text-muted)',
                borderRadius: 4, padding: '1px 6px', letterSpacing: '.04em',
              }}>{t('item_authoring.coming_soon')}</span>
            </button>
          </div>
        </div>
      )}

      {/* PAS 2 · CONSTRUCCIÓ */}
      {step === 2 && (
        <div>
          <div style={{
            border: '0.5px solid var(--border)', borderRadius: 12, background: 'var(--white)',
            padding: 18, marginBottom: 20,
          }}>
            <p style={sectionTitle}>{t('item_authoring.confirm_basesize')}</p>
            {/* C2 — completesa progressiva: la talla base s'informa quan es carreguen mesures dels
                POMs de l'item, no abans. Sense graduació no hi ha d'on treure la llista de talles,
                i això es DIU (no es deixa un buit mut ni es bloqueja el pas). */}
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
              {chosenRuleset
                ? t('item_authoring.basesize_from', { system: chosenRuleset.size_system_nom || '' })
                : t('item_authoring.basesize_no_source')}
            </p>
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
              {sizeDefs.length === 0 && chosenRuleset && (
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
                  {t('item_authoring.basesize_none')}
                </span>
              )}
            </div>
          </div>

          <p style={sectionTitle}>{t('item_authoring.measurements')}</p>
          <MeasurementBaseGrid garmentTypeItemId={itemId} />
        </div>
      )}

      {/* Navegació */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 28, paddingTop: 16, borderTop: '0.5px solid var(--border)' }}>
        <button type="button" onClick={goBack} style={btnSecondary}>
          ← {step === 1 ? t('item_authoring.cancel') : t('item_authoring.back')}
        </button>
        {step < 2 ? (
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
  )
}

const fieldLabel = {
  fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)',
  textTransform: 'uppercase', display: 'block', marginBottom: 6,
}
