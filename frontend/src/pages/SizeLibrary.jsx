import { useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import RunsCataleg from "../components/SizeLibrary/RunsCataleg"
import SizeAuthoringDrawer from "../components/SizeAuthoringDrawer"

// A2 (08/08) — AQUESTA PANTALLA ERA EL SELECTOR DE PRESETS i ara és el CATÀLEG DE RUNS.
//
// La maqueta v3 ho diu amb totes les lletres: «els presets amb graduació dins han desaparegut.
// Un run és una escala; els increments de POM viuen als jocs de regles. Aquí no hi ha ni un
// delta». El que hi havia —`SizingProfileSelector` + `SizeSetDetail`— era justament allò: chips
// d'eixos i targetes de preset amb la graduació a dins.
//
// ⚠️ ELS DOS COMPONENTS NO S'ESBORREN, i el cens diu per què: `SizingProfileSelector` i
// `SizeSetDetail` NOMÉS els muntava aquesta pàgina, o sigui que retirar-los d'aquí els deixa
// sense cap consumidor. Esborrar-los seria una decisió d'abast que aquest tram no té; queden al
// disc, sense muntar, i anotats al report.
//
// EL DRAWER D'AUTORIA ES QUEDA: és qui crea runs de debò (i `GradingRuleSets` també el munta),
// i és on porta el deep-link `?prefill=` de l'ImportWizard.

// 1C-3b — ?prefill= (base64 unicode-safe d'un JSON), mateix patró que SizeMapSetup.readPrefill.
function readPrefill(p) {
  if (!p) return null
  try { return JSON.parse(decodeURIComponent(escape(atob(p)))) } catch { return null }
}

export default function SizeLibrary() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()

  const [msg, setMsg] = useState(null)
  // Si venim de l'ImportWizard amb ?prefill=, obrim el drawer auto-omplert (decisió ii: sense represa).
  const [drawerPrefill, setDrawerPrefill] = useState(() => readPrefill(searchParams.get('prefill')))
  const [drawerOpen, setDrawerOpen] = useState(() => !!readPrefill(searchParams.get('prefill')))
  const [selectorKey, setSelectorKey] = useState(0)

  // Treu ?prefill de la URL (mantenint ?target) perquè el drawer no es re-obri en re-render.
  const clearPrefillParam = () => {
    if (!searchParams.get('prefill')) return
    const next = new URLSearchParams(searchParams)
    next.delete('prefill')
    setSearchParams(next, { replace: true })
  }

  return (
    <div style={{ padding: '0 20px 60px' }}>
      {msg && (
        <div role="alert" style={{
          padding: '8px 12px', margin: '12px 0', borderRadius: 'var(--r-ctrl)',
          fontSize: 'var(--fs-body)', display: 'flex', justifyContent: 'space-between',
          background: msg.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          border: `1px solid ${msg.type === 'ok' ? 'var(--ok)' : 'var(--err)'}`,
          color: msg.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>
          {msg.text}
          <button onClick={() => setMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>×</button>
        </div>
      )}

      <RunsCataleg key={selectorKey} onNou={() => setDrawerOpen(true)} />

      {/* Drawer d'autoria de talles (1C-3): prefill nul en autoria directa, o el de ?prefill
          quan venim de l'ImportWizard (1C-3b). És qui CREA runs; la fitxa només els edita. */}
      <SizeAuthoringDrawer
        open={drawerOpen}
        prefill={drawerPrefill}
        onClose={() => { setDrawerOpen(false); setDrawerPrefill(null); clearPrefillParam() }}
        onComplete={() => {
          setDrawerOpen(false)
          setDrawerPrefill(null)
          clearPrefillParam()
          setSelectorKey(k => k + 1)
          setMsg({ type: 'ok', text: t('size_library.created') })
        }}
      />
    </div>
  )
}
