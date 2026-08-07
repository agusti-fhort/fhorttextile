import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { TARGETS, CONSTRUCTIONS, FITS, groupLabel } from "./grading/gradingAxes"
import { Chip } from "./grading/wizardUI"
import { sizeSystems, garmentGroups } from "../api/endpoints"

// RunRestrictionEditor (C5 · 2026-08-07) — editar a mà les 4 capes de restricció d'un RUN.
//
// Fins ara les capes de N1 només es podien omplir des de la data migration que les va deduir.
// Un run que neix nou —o un que la deducció no va poder classificar— es quedava mut per sempre.
// Això és el gest que faltava, i és el MATEIX vocabulari i els MATEIXOS chips de N2: aquí no
// neix cap llista nova, perquè el codi és la identitat i el nom només és presentació.
//
// 🔑 Buit no és una capa «apagada»: és una capa NO DECLARADA, i per tant no exclou ningú (llei
// de N1 · D-31.3). El pas 3 del wizard ORDENA per proximitat i no amaga res, o sigui que un run
// sense capes surt igualment — només que sense res a dir sobre a qui s'assembla. El text de sota
// de cada capa ho diu amb aquestes paraules per no deixar-ho a la intuïció de qui edita.

// El chip és el de la casa (`grading/wizardUI.jsx`), el MATEIX que tria el target al wizard i el
// fit a Graduació. Aquí hi havia una factoria d'estil pròpia (S37 · vet del guardia-ui): mateixa
// capa, quart aspecte, i l'estat «triat» amb 2.8:1 de contrast quan el color n'era l'únic senyal.
function Capa({ titol, opcions, triats, onToggle, buida }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{
        fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".06em",
        textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 5,
      }}>{titol}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
        {opcions.map(o => (
          <Chip key={o.codi} active={triats.includes(o.codi)} onClick={() => onToggle(o.codi)}>
            {o.etiqueta}
          </Chip>
        ))}
      </div>
      {triats.length === 0 && (
        <div style={{ fontSize: 'var(--fs-label)', color: "var(--text-muted)", marginTop: 4, fontStyle: "italic" }}>
          {buida}
        </div>
      )}
    </div>
  )
}

export default function RunRestrictionEditor({ run, onSaved, onCancel }) {
  const { t, i18n } = useTranslation()
  const [triats, setTriats] = useState({
    target_codis: run?.target_codis || [],
    grup_codis: run?.grup_codis || [],
    construccio_codis: run?.construccio_codis || [],
    fit_codis: run?.fit_codis || [],
  })
  // Els grups surten de la BD, no de la llista estàtica: `fhort` en té 12 (TOPS-KNIT,
  // DRESSES-FULL, NEWBORN…) i la constant del front només en declara 7. Editar amb la llista
  // curta faria desaparèixer en silenci els grups que el run ja té assignats.
  const [grups, setGrups] = useState(null)
  const [desant, setDesant] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let viu = true
    garmentGroups.list({ page_size: 200 })
      .then(r => { if (viu) setGrups(r.data?.results ?? (Array.isArray(r.data) ? r.data : [])) })
      .catch(() => { if (viu) setGrups([]) })
    return () => { viu = false }
  }, [])

  const toggle = (capa, codi) => setTriats(s => ({
    ...s,
    [capa]: s[capa].includes(codi) ? s[capa].filter(c => c !== codi) : [...s[capa], codi],
  }))

  const desa = () => {
    setDesant(true)
    setError(null)
    sizeSystems.update(run.id, triats)
      .then(r => onSaved && onSaved(r.data))
      .catch(e => setError(e.response?.data?.detail || e.response?.data?.tipus_escala?.[0]
                           || t('size_library.restrictions_error')))
      .finally(() => setDesant(false))
  }

  const opcionsGrup = (grups ?? []).map(g => ({
    codi: g.codi, etiqueta: groupLabel(g.codi, i18n.language) || g.nom || g.codi,
  }))
  // Un codi que el run ja porta però que no és a la llista viva no es pot perdre pel camí.
  const orfes = triats.grup_codis
    .filter(c => !opcionsGrup.some(o => o.codi === c))
    .map(c => ({ codi: c, etiqueta: c }))

  // El fons és `#fdf9f5`, el crema dels panells germans d'aquesta MATEIXA pantalla
  // (`SizeSetDetail.jsx`: historial, zebra, calaixos). Aquí hi havia `#fdfaf6`, a ΔE 0.45 —
  // un 4t crema accidental, no una decisió. Segueix sent literal perquè el valor encara no té
  // token (10 usos en 6 fitxers esperen bateig); v. REPORT_C5_CHIP_S37 §7.
  return (
    <div style={{
      border: "1px solid var(--gold-border)", borderRadius: 6, padding: "12px 14px",
      background: "#fdf9f5", marginBottom: 14,
    }}>
      <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600, marginBottom: 4 }}>
        {t('size_library.restrictions_title')}
      </div>
      <div style={{ fontSize: 'var(--fs-label)', color: "var(--text-muted)", marginBottom: 10 }}>
        {t('size_library.restrictions_help')}
      </div>

      <Capa titol={t('size_library.layer_target')}
            opcions={TARGETS.map(x => ({ codi: x.codi, etiqueta: t(`model_wizard.target_${x.codi}`, x.nom_en) }))}
            triats={triats.target_codis} onToggle={c => toggle('target_codis', c)}
            buida={t('size_library.layer_empty')} />
      <Capa titol={t('size_library.layer_group')}
            opcions={[...opcionsGrup, ...orfes]}
            triats={triats.grup_codis} onToggle={c => toggle('grup_codis', c)}
            buida={t('size_library.layer_empty')} />
      <Capa titol={t('size_library.layer_construction')}
            opcions={CONSTRUCTIONS.map(x => ({ codi: x.codi, etiqueta: t(`model_wizard.construction_${x.codi}`, x.nom_en) }))}
            triats={triats.construccio_codis} onToggle={c => toggle('construccio_codis', c)}
            buida={t('size_library.layer_empty')} />
      <Capa titol={t('size_library.layer_fit')}
            opcions={FITS.map(x => ({ codi: x.codi, etiqueta: t(`model_wizard.fit_${x.codi}`, x.nom_en) }))}
            triats={triats.fit_codis} onToggle={c => toggle('fit_codis', c)}
            buida={t('size_library.layer_empty')} />

      {error && (
        <div style={{ fontSize: 'var(--fs-label)', color: "var(--err)", marginBottom: 8 }}>{error}</div>
      )}
      <div style={{ display: "flex", gap: 6 }}>
        {/* Acció primària: la parella de la casa `--warn` + `--white` (6.73:1), la mateixa que
            el botó primari del wizard (`ModelWizard.jsx:942`) i que el `Chip` triat d'aquí
            sobre. Abans era `--gold` sobre `--gold-pale` = 2.80:1, el mateix defecte que el
            vet va mesurar al chip: tokenitzar-lo no el va arreglar. V. REPORT §8. */}
        <button type="button" onClick={desa} disabled={desant} style={{
          padding: "5px 12px", borderRadius: 4, fontSize: 'var(--fs-body)',
          fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
          background: "var(--warn)", color: "var(--white)", border: "none",
          cursor: desant ? "not-allowed" : "pointer", opacity: desant ? .6 : 1,
        }}>{desant ? '…' : t('size_library.restrictions_save')}</button>
        <button type="button" onClick={onCancel} style={{
          padding: "5px 12px", borderRadius: 4, fontSize: 'var(--fs-body)',
          fontFamily: "IBM Plex Mono, monospace",
          background: "var(--white)", color: "var(--text-muted)", border: "1px solid var(--border)",
          cursor: "pointer",
        }}>{t('size_library.restrictions_cancel')}</button>
      </div>
    </div>
  )
}
