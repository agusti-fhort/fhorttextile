
import { useState, useEffect } from "react"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

const TARGET_ICONS = {
  WOMAN:"♀", MAN:"♂", UNISEX_ADULT:"◎",
  BABY_GIRL:"♀°", BABY_BOY:"♂°", BABY_UNISEX:"◉",
  TODDLER_GIRL:"♀¹", TODDLER_BOY:"♂¹",
  GIRL:"♀²", BOY:"♂²",
  TEEN_GIRL:"♀³", TEEN_BOY:"♂³", MATERNITY:"♀♥",
}

const TARGET_ORDER = [
  "WOMAN","MAN","UNISEX_ADULT",
  "BABY_GIRL","BABY_BOY","BABY_UNISEX",
  "TODDLER_GIRL","TODDLER_BOY",
  "GIRL","BOY","TEEN_GIRL","TEEN_BOY","MATERNITY"
]

const STEPS = ["Target","Construcció","Size Set","Confirma"]

function StepBar({ step }) {
  return (
    <div style={{ display:"flex", alignItems:"center", marginBottom:20, gap:0 }}>
      {STEPS.map((s, i) => {
        const done = i < step, active = i === step
        return (
          <div key={s} style={{ display:"flex", alignItems:"center" }}>
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:3 }}>
              <div style={{
                width:26, height:26, borderRadius:"50%",
                background: active ? "#c27a2a" : done ? "#f0f9f0" : "#f5f0ea",
                border: `1px solid ${active ? "#c27a2a" : done ? "#3b6d11" : "#e0d5c5"}`,
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:11, fontFamily:"IBM Plex Mono, monospace",
                color: active ? "#fff" : done ? "#3b6d11" : "#868685",
              }}>
                {done ? "✓" : i+1}
              </div>
              <div style={{
                fontSize:9, whiteSpace:"nowrap",
                fontFamily:"IBM Plex Mono, monospace",
                color: active ? "#c27a2a" : done ? "#3b6d11" : "#868685",
              }}>{s}</div>
            </div>
            {i < STEPS.length-1 && (
              <div style={{
                width:32, height:1, margin:"0 4px", marginBottom:16,
                background: i < step ? "#c0dd97" : "#e0d5c5",
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function SizingProfileWizard({ onComplete, onCancel, initialValues = {} }) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [step, setStep] = useState(0)

  // Dades carregades
  const [targets, setTargets] = useState([])
  const [constructions, setConstructions] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(false)

  // Seleccions
  const [selTarget, setSelTarget] = useState(initialValues.target || null)
  const [selConstruction, setSelConstruction] = useState(initialValues.construction || null)
  const [selProfile, setSelProfile] = useState(null)
  const [selSizes, setSelSizes] = useState([])
  const [selBase, setSelBase] = useState(null)

  const headers = { Authorization: `Bearer ${token}` }

  // Carregar targets
  useEffect(() => {
    fetch(`${API}/api/v1/targets/`, { headers })
      .then(r => r.json())
      .then(d => {
        const all = Array.isArray(d) ? d : (d.results || [])
        const sorted = TARGET_ORDER.map(c => all.find(t => t.codi === c)).filter(Boolean)
        setTargets(sorted)
      })
      .catch(() => {
        // Mock
        setTargets([
          {id:1,codi:"WOMAN",nom_en:"Woman",nom_cat:"Dona"},
          {id:2,codi:"MAN",nom_en:"Man",nom_cat:"Home"},
          {id:4,codi:"BABY_GIRL",nom_en:"Baby Girl",nom_cat:"Nadó nena"},
          {id:5,codi:"BABY_BOY",nom_en:"Baby Boy",nom_cat:"Nadó nen"},
          {id:9,codi:"GIRL",nom_en:"Girl",nom_cat:"Nena"},
          {id:10,codi:"BOY",nom_en:"Boy",nom_cat:"Nen"},
        ])
      })

    fetch(`${API}/api/v1/construction-types/`, { headers })
      .then(r => r.json())
      .then(d => setConstructions(Array.isArray(d) ? d : (d.results || [])))
      .catch(() => {
        setConstructions([
          {id:1,codi:"WOVEN",nom_en:"Woven",nom_cat:"Teixit pla"},
          {id:2,codi:"KNIT",nom_en:"Knit",nom_cat:"Punt jersey"},
          {id:3,codi:"STRETCH_KNIT",nom_en:"Stretch Knit",nom_cat:"Punt elàstic"},
          {id:4,codi:"TECHNICAL",nom_en:"Technical",nom_cat:"Tècnic"},
        ])
      })
  }, [token])

  // Carregar profiles quan target+construction seleccionats
  useEffect(() => {
    if (!selTarget || !selConstruction) return
    setLoading(true)
    fetch(`${API}/api/v1/sizing-profiles/?target=${selTarget}&construction=${selConstruction}`, { headers })
      .then(r => r.json())
      .then(d => {
        setProfiles(Array.isArray(d) ? d : (d.results || []))
        setLoading(false)
      })
      .catch(() => {
        setProfiles([{
          id:1,
          size_system: { id:1, codi:"ALPHA_EU_W", nom:"Alpha EU — Women" },
          grading_rule_set: { id:1, nom:"EU Knit Woman Regular", is_system_default:true },
          fit_type_nom:"Regular",
          is_default:true, is_custom:false, version:1,
          size_definitions: [
            {size_label:"XXS"},{size_label:"XS"},{size_label:"S"},
            {size_label:"M"},{size_label:"L"},{size_label:"XL"},{size_label:"XXL"},
          ],
          grading_rules_preview: [
            {pom_codi:"POM-001",pom_nom_en:"Chest width",increment:2.0},
            {pom_codi:"POM-003",pom_nom_en:"Waist width",increment:1.5},
          ]
        }])
        setLoading(false)
      })
  }, [selTarget, selConstruction])

  // Quan selecciona un profile, preseleccionar totes les talles
  useEffect(() => {
    if (selProfile) {
      const defs = selProfile.size_definitions || []
      setSelSizes(defs.map(s => s.size_label))
      // Talla base = la central
      const mid = defs[Math.floor(defs.length / 2)]
      setSelBase(mid?.size_label || null)
    }
  }, [selProfile])

  const canNext = [
    !!selTarget,
    !!selConstruction,
    !!selProfile && selSizes.length > 0 && !!selBase,
    true,
  ][step]

  const handleConfirm = () => {
    if (!selProfile) return
    const sizeRun = (selProfile.size_definitions || [])
      .filter(s => selSizes.includes(s.size_label))
      .map(s => s.size_label)
      .join('·')

    onComplete({
      sizing_profile_id: selProfile.id,
      size_system_id: selProfile.size_system?.id,
      size_system_nom: selProfile.size_system?.nom,
      grading_rule_set_id: selProfile.grading_rule_set?.id,
      grading_rule_set_nom: selProfile.grading_rule_set?.nom,
      base_size_label: selBase,
      size_run_model: sizeRun,
      target_codi: selTarget,
      construction_codi: selConstruction,
    })
  }

  return (
    <div style={{ fontFamily:"IBM Plex Mono, monospace", maxWidth:680 }}>
      <StepBar step={step} />

      {/* STEP 0 — Target */}
      {step === 0 && (
        <div>
          <div style={{ fontSize:11, color:"#868685", marginBottom:12 }}>
            Per a qui és la peça?
          </div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
            {targets.map(t => (
              <button key={t.codi} onClick={() => setSelTarget(t.codi)} style={{
                padding:"8px 14px", borderRadius:6, cursor:"pointer",
                background: selTarget===t.codi ? "#f5e6d0" : "#fff",
                color: selTarget===t.codi ? "#c27a2a" : "#1d1d1b",
                border:`1px solid ${selTarget===t.codi ? "#c27a2a" : "#e0d5c5"}`,
                fontFamily:"IBM Plex Mono, monospace", fontSize:11,
                display:"flex", flexDirection:"column", alignItems:"center", gap:3,
                minWidth:78,
              }}>
                <span style={{ fontSize:16 }}>{TARGET_ICONS[t.codi]||"◆"}</span>
                <span style={{ fontWeight: selTarget===t.codi ? 600 : 400 }}>{t.nom_en}</span>
                <span style={{ fontSize:9, color: selTarget===t.codi ? "#c27a2a" : "#868685" }}>
                  {t.nom_cat}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* STEP 1 — Construcció */}
      {step === 1 && (
        <div>
          <div style={{ fontSize:11, color:"#868685", marginBottom:12 }}>
            Com és el teixit de la peça?
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            {constructions.map(c => (
              <button key={c.codi} onClick={() => setSelConstruction(c.codi)} style={{
                padding:"12px 16px", borderRadius:6, cursor:"pointer", textAlign:"left",
                background: selConstruction===c.codi ? "#f5e6d0" : "#fff",
                color: "#1d1d1b",
                border:`1.5px solid ${selConstruction===c.codi ? "#c27a2a" : "#e0d5c5"}`,
                fontFamily:"IBM Plex Mono, monospace",
                display:"flex", justifyContent:"space-between", alignItems:"center",
              }}>
                <div>
                  <div style={{ fontSize:13, fontWeight: selConstruction===c.codi ? 600 : 400, color: selConstruction===c.codi ? "#c27a2a" : "#1d1d1b" }}>
                    {c.nom_en}
                  </div>
                  <div style={{ fontSize:10, color:"#868685", marginTop:2 }}>
                    {c.nom_cat}
                    {c.mesures_en_mitja && " · Spec en HALF (½)"}
                  </div>
                </div>
                {selConstruction===c.codi && (
                  <span style={{ color:"#c27a2a", fontSize:16 }}>✓</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* STEP 2 — Size Set */}
      {step === 2 && (
        <div>
          <div style={{ fontSize:11, color:"#868685", marginBottom:12 }}>
            {loading ? "Carregant size sets..." : `${profiles.length} sistemes disponibles. Selecciona i ajusta el run de talles.`}
          </div>

          {profiles.map(p => {
            const isSelected = selProfile?.id === p.id
            return (
              <div key={p.id} style={{
                border:`1.5px solid ${isSelected ? "#c27a2a" : "#e0d5c5"}`,
                borderRadius:8, padding:"14px 16px", marginBottom:10,
                background: isSelected ? "#fdf6ee" : "#fff", cursor:"pointer",
              }} onClick={() => setSelProfile(p)}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:isSelected?10:0 }}>
                  <div>
                    <span style={{ fontSize:13, fontWeight:600, color: isSelected?"#c27a2a":"#1d1d1b" }}>
                      {p.size_system?.nom}
                    </span>
                    <span style={{ fontSize:10, color:"#868685", marginLeft:8 }}>
                      {p.fit_type_nom}
                    </span>
                  </div>
                  <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                    {p.is_custom
                      ? <span style={{ fontSize:9, padding:"1px 6px", borderRadius:3, background:"#f5e6d0", color:"#c27a2a", border:"1px solid #e0c8a0" }}>Custom</span>
                      : <span style={{ fontSize:9, padding:"1px 6px", borderRadius:3, background:"#f0f9f0", color:"#3b6d11", border:"1px solid #c0dd97" }}>ISO</span>
                    }
                    {isSelected && <span style={{ color:"#c27a2a" }}>✓</span>}
                  </div>
                </div>

                {isSelected && (
                  <div>
                    {/* Selector de talles */}
                    <div style={{ fontSize:10, color:"#868685", marginBottom:6 }}>
                      Selecciona les talles del run:
                    </div>
                    <div style={{ display:"flex", flexWrap:"wrap", gap:5, marginBottom:10 }}>
                      {(p.size_definitions||[]).map(s => {
                        const checked = selSizes.includes(s.size_label)
                        return (
                          <button key={s.size_label}
                            onClick={e => {
                              e.stopPropagation()
                              setSelSizes(prev =>
                                checked
                                  ? prev.filter(x => x !== s.size_label)
                                  : [...prev, s.size_label]
                              )
                              if (!checked && !selBase) setSelBase(s.size_label)
                            }}
                            style={{
                              padding:"4px 10px", borderRadius:4, fontSize:11,
                              background: checked ? "#f5e6d0" : "#f5f0ea",
                              color: checked ? "#c27a2a" : "#868685",
                              border:`1px solid ${checked ? "#c27a2a" : "#e0d5c5"}`,
                              cursor:"pointer", fontFamily:"IBM Plex Mono, monospace",
                            }}>
                            {s.size_label}
                          </button>
                        )
                      })}
                    </div>

                    {/* Selector talla base */}
                    {selSizes.length > 0 && (
                      <div>
                        <div style={{ fontSize:10, color:"#868685", marginBottom:6 }}>
                          Talla base (★):
                        </div>
                        <div style={{ display:"flex", flexWrap:"wrap", gap:5 }}>
                          {selSizes.map(s => (
                            <button key={s}
                              onClick={e => { e.stopPropagation(); setSelBase(s) }}
                              style={{
                                padding:"4px 10px", borderRadius:4, fontSize:11,
                                background: selBase===s ? "#c27a2a" : "#fff",
                                color: selBase===s ? "#fff" : "#1d1d1b",
                                border:`1px solid ${selBase===s ? "#c27a2a" : "#e0d5c5"}`,
                                cursor:"pointer", fontFamily:"IBM Plex Mono, monospace",
                                fontWeight: selBase===s ? 600 : 400,
                              }}>
                              {s}{selBase===s ? " ★" : ""}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* STEP 3 — Resum */}
      {step === 3 && selProfile && (
        <div>
          <div style={{ fontSize:11, color:"#868685", marginBottom:14 }}>
            Confirma la configuració de talles per a aquest model:
          </div>
          <div style={{
            border:"1px solid #e0d5c5", borderRadius:8, padding:"16px",
            background:"#fdf9f5",
          }}>
            {[
              ["Target", targets.find(t=>t.codi===selTarget)?.nom_en || selTarget],
              ["Construcció", constructions.find(c=>c.codi===selConstruction)?.nom_en || selConstruction],
              ["Sistema", selProfile.size_system?.nom],
              ["Grading", selProfile.grading_rule_set?.nom],
              ["Run de talles", selSizes.join(" · ")],
              ["Talla base", selBase ? `${selBase} ★` : "—"],
            ].map(([label, val]) => (
              <div key={label} style={{
                display:"grid", gridTemplateColumns:"130px 1fr",
                padding:"5px 0", borderBottom:"1px solid #f0e8d8",
                fontFamily:"IBM Plex Mono, monospace", fontSize:12,
              }}>
                <span style={{ color:"#868685" }}>{label}</span>
                <span style={{ color:"#1d1d1b", fontWeight: label==="Talla base"?600:400 }}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navegació */}
      <div style={{ display:"flex", gap:8, marginTop:20, justifyContent:"flex-end" }}>
        {step > 0 && (
          <button onClick={() => setStep(s => s-1)} style={{
            padding:"7px 16px", borderRadius:4, fontSize:11, cursor:"pointer",
            background:"#fff", color:"#868685", border:"1px solid #e0d5c5",
            fontFamily:"IBM Plex Mono, monospace",
          }}>← Enrere</button>
        )}
        {onCancel && step === 0 && (
          <button onClick={onCancel} style={{
            padding:"7px 16px", borderRadius:4, fontSize:11, cursor:"pointer",
            background:"#fff", color:"#868685", border:"1px solid #e0d5c5",
            fontFamily:"IBM Plex Mono, monospace",
          }}>Cancel·lar</button>
        )}
        {step < STEPS.length-1 ? (
          <button onClick={() => setStep(s => s+1)} disabled={!canNext} style={{
            padding:"7px 18px", borderRadius:4, fontSize:11,
            background: canNext ? "#f5e6d0" : "#f5f0ea",
            color: canNext ? "#c27a2a" : "#c8b89a",
            border:`1px solid ${canNext ? "#c27a2a" : "#e0d5c5"}`,
            cursor: canNext ? "pointer" : "not-allowed",
            fontFamily:"IBM Plex Mono, monospace",
          }}>Següent →</button>
        ) : (
          <button onClick={handleConfirm} style={{
            padding:"7px 18px", borderRadius:4, fontSize:11, cursor:"pointer",
            background:"#f5e6d0", color:"#c27a2a", border:"1px solid #c27a2a",
            fontFamily:"IBM Plex Mono, monospace", fontWeight:600,
          }}>✓ Confirmar</button>
        )}
      </div>
    </div>
  )
}
