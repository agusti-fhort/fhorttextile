import { useState } from "react"
import { useSearchParams } from "react-router-dom"
import { SizeSetDetail } from "../components/SizeSetDetail"
import { SizingProfileSelector } from "../components/SizingProfileSelector"
import SizeAuthoringDrawer from "../components/SizeAuthoringDrawer"
import useAuthStore from "../store/auth"
import { sizingProfiles } from "../api/endpoints"

export default function SizeLibrary() {
  const [searchParams] = useSearchParams()
  const canConfigure = !!useAuthStore(s => s.user)?.capabilities?.includes('configure')

  const [detailProfileId, setDetailProfileId] = useState(null)
  const [msg, setMsg] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectorKey, setSelectorKey] = useState(0)

  const handleClone = async (profile) => {
    try {
      const { data: d } = await sizingProfiles.clone(profile.id, { nom_client: `Custom ${profile.size_system?.nom}` })
      setMsg({ type: 'ok', text: d?.missatge })
    } catch (e) {
      if (e.response) {
        setMsg({ type: 'error', text: e.response.data?.error || 'Error clonant el perfil' })
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
          <h1 style={{ fontSize: 18, fontWeight: 500, color: "#1d1d1b", margin: "0 0 4px" }}>
            Size Library
          </h1>
          <div style={{ fontSize: 12, color: "#868685" }}>
            Sistemes de talles, runs i grading disponibles per al teu catàleg.
          </div>
        </div>
        {canConfigure && (
          <button
            onClick={() => setDrawerOpen(true)}
            style={{
              padding: "8px 14px", borderRadius: 4, fontSize: 12, cursor: "pointer",
              background: "#f5e6d0", color: "#c27a2a", border: "1px solid #c27a2a",
              fontFamily: "IBM Plex Mono, monospace", whiteSpace: "nowrap",
              display: "inline-flex", alignItems: "center", gap: 6,
            }}
          >
            <i className="ti ti-plus" style={{ fontSize: 13 }} /> Crear / Importar
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
            border: "1px solid #e0d5c5", borderRadius: 8,
            padding: "16px", background: "#fdf9f5",
            position: "sticky", top: 24,
            maxHeight: "calc(100vh - 120px)", overflowY: "auto",
          }}>
            <SizeSetDetail
              profileId={detailProfileId}
              onClose={() => setDetailProfileId(null)}
            />
          </div>
        )}
      </div>

      {/* Drawer d'autoria de talles (1C-3) — autoria directa, prefill nul. */}
      <SizeAuthoringDrawer
        open={drawerOpen}
        prefill={null}
        onClose={() => setDrawerOpen(false)}
        onComplete={() => {
          setDrawerOpen(false)
          setSelectorKey(k => k + 1)
          setMsg({ type: 'ok', text: 'Sistema de talles creat' })
        }}
      />
    </div>
  )
}
