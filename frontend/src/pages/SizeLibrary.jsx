import { useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { SizeSetDetail } from "../components/SizeSetDetail"
import { SizingProfileSelector } from "../components/SizingProfileSelector"
import SizeAuthoringDrawer from "../components/SizeAuthoringDrawer"
import useAuthStore from "../store/auth"
import { sizingProfiles } from "../api/endpoints"

// 1C-3b — ?prefill= (base64 unicode-safe d'un JSON), mateix patró que SizeMapSetup.readPrefill.
function readPrefill(p) {
  if (!p) return null
  try { return JSON.parse(decodeURIComponent(escape(atob(p)))) } catch { return null }
}

export default function SizeLibrary() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const canConfigure = !!useAuthStore(s => s.user)?.capabilities?.includes('configure')

  const [detailProfileId, setDetailProfileId] = useState(null)
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

  const handleClone = async (profile) => {
    try {
      const { data: d } = await sizingProfiles.clone(profile.id, { nom_client: `Custom ${profile.size_system?.nom}` })
      setMsg({ type: 'ok', text: d?.missatge })
    } catch (e) {
      if (e.response) {
        setMsg({ type: 'error', text: e.response.data?.error || t('size_library.clone_error') })
      } else {
        setMsg({ type: 'error', text: String(e) })
      }
    }
  }

  return (
    <div style={{ padding: "24px", maxWidth: 1100, margin: "0 auto", fontFamily: "IBM Plex Mono, monospace" }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 500, color: "var(--text-main)", margin: "0 0 4px" }}>
            {t('nav.size_library')}
          </h1>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {t('size_library.subtitle')}
          </div>
        </div>
        {canConfigure && (
          <button
            onClick={() => { setDrawerPrefill(null); setDrawerOpen(true) }}
            style={{
              padding: "8px 14px", borderRadius: 4, fontSize: 12, cursor: "pointer",
              background: "#f5e6d0", color: "var(--gold)", border: "1px solid var(--gold)",
              fontFamily: "IBM Plex Mono, monospace", whiteSpace: "nowrap",
              display: "inline-flex", alignItems: "center", gap: 6,
            }}
          >
            <i className="ti ti-plus" style={{ fontSize: 13 }} /> {t('size_library.create_import')}
          </button>
        )}
      </div>

      {/* Missatge global */}
      {msg && (
        <div style={{
          padding: "8px 12px", marginBottom: 16, borderRadius: 4, fontSize: 11,
          background: msg.type === 'ok' ? "#f0f9f0" : "#fff0f0",
          border: `1px solid ${msg.type === 'ok' ? "#c0dd97" : "#f09595"}`,
          color: msg.type === 'ok' ? "#3b6d11" : "#a32d2d",
          display: "flex", justifyContent: "space-between",
        }}>
          {msg.text}
          <button onClick={() => setMsg(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}>×</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: detailProfileId ? "1fr 420px" : "1fr", gap: 24, alignItems: "start" }}>
        <SizingProfileSelector
          key={selectorKey}
          initialTarget={searchParams.get('target')}
          onDetail={(profile) => setDetailProfileId(profile.id)}
          onClone={handleClone}
          onSelectionChange={() => setDetailProfileId(null)}
        />

        {/* Panel de detall */}
        {detailProfileId && (
          <div style={{
            border: "1px solid var(--border)", borderRadius: 8,
            padding: "16px", background: "#fdf9f5",
            position: "sticky", top: 24,
            maxHeight: "calc(100vh - 120px)", overflowY: "auto",
          }}>
            <SizeSetDetail
              profileId={detailProfileId}
              onClose={() => setDetailProfileId(null)}
              onRefresh={() => { setDetailProfileId(null); setSelectorKey(k => k + 1) }}
            />
          </div>
        )}
      </div>

      {/* Drawer d'autoria de talles (1C-3) — prefill nul en autoria directa, o el de
          ?prefill quan venim de l'ImportWizard (1C-3b). */}
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
