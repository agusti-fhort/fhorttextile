import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models as modelsApi } from '../api/endpoints'
import AssetNavigator from '../components/assets/AssetNavigator'
import PageMenu from '../components/ui/PageMenu'
import { botoSec } from '../components/ui/buttons'

// D10 — porta-menú de la fitxa tècnica (S03b · P6).
//
// El gate de `tech_sheet` viu al backend, a open-task (allow-list per usuari). Aquesta pàgina
// NO reimplementa cap comprovació de permisos: crida openTask i navega NOMÉS en èxit, igual
// que WorkPlan.jsx:240-249 i TaskTree.jsx:109-118. Si el backend diu que el tipus no és a
// l'allow-list, s'ofereix "obrir en consulta" (sense task_id → l'editor no imputa temps).
//
// Sidebar-com-a-ruta: les entrades del Sidebar són NavLink declaratius (`to:`); no hi ha cap
// precedent d'entrada amb onClick. Per això el menú apunta a aquesta pàgina en comptes d'obrir
// un modal des del Sidebar: mateix resultat per a l'usuari, sense trencar el patró del menú.
//
// S03c · C5.1 — la llista plana de 12 models (i la seva cerca pròpia) han estat substituïdes per
// l'AssetNavigator en mode='models', INLINE: aquesta pàgina no és una capa sobre res, és la
// pàgina sencera. La cerca, les facetes Client▸Any▸Temporada i el debounce ara viuen al
// navegador, que és el mateix que fa servir l'editor — una sola superfície de navegació d'actius.
// `obrir` i `obrirConsulta` no s'han tocat: el navegador retorna un model i prou.

export default function TechSheetEntry() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState(null)
  // Quan el backend rebutja per allow-list, guardem el model per oferir la consulta.
  const [consultaModel, setConsultaModel] = useState(null)
  // Memòria de camí a nivell de PÀGINA (mai localStorage): tornar enrere des d'un model rebutjat
  // no ha de fer recomençar la navegació pel client i la temporada.
  const [nav, setNav] = useState({ tab: 'models', cust: null, any: null, temp: null, modelId: null, gtId: null, gtiId: null })

  const obrirConsulta = (modelId) => navigate(`/models/${modelId}/fitxa`)

  const obrir = async (model) => {
    if (!model) return
    setBusyId(model.id)
    setError(null)
    setConsultaModel(null)
    try {
      const res = await modelsApi.openTask(model.id, 'tech_sheet')
      const taskId = res?.data?.task_id
      if (!taskId) {
        // Resposta inesperada: NO degradem silenciosament a consulta. Val més que el sistema
        // sembli trencat que amagar un fallo real fent passar per consulta el que no ho és.
        setError(t('tech_sheet_entry.unexpected_response'))
        return
      }
      navigate(`/models/${model.id}/fitxa?task_id=${taskId}`)
    } catch (e) {
      const status = e?.response?.status
      const code = e?.response?.data?.code
      if (status === 403 && code === 'task_type_not_allowed') {
        // Bloqueig tou: l'usuari no té tech_sheet a l'allow-list, però pot consultar-la.
        setConsultaModel(model)
      } else {
        // Bloqueig dur (sense EXECUTE_TASKS, sense perfil, 409, timeout…): error, sense consulta.
        setError(e?.response?.data?.error || t('tech_sheet_entry.open_error'))
      }
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA. Aquesta porta no en tenia i, com que és una PORTA, era la
          pantalla del producte on més falta feia: qui hi entra i decideix no obrir cap fitxa no
          tenia cap manera de sortir-ne que no fos el menú lateral. Sense seccions ni acció, la
          barra queda amb només la fletxa (§8b.2). El padding arrel de 24px sobrava: el `<main>`
          ja el dona (§3), i aquí anaven a sobre l'un de l'altre. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu backTo="/" backTitle={t('tech_sheet_entry.back_title')} />
      </div>

    <div style={{ paddingTop: 16, maxWidth: 860 }}>
      {/* §8b.3 · identitat sobre el fons de pàgina. El subtítol baixa a caption i a `--text-soft`
          (`--text-muted` és DEPRECAT per la §1b(c) i dona 3.64:1). */}
      <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500,
                   color: 'var(--text-main)', marginBottom: 4 }}>
        {t('tech_sheet_entry.title')}
      </h1>
      <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', marginBottom: 20 }}>
        {t('tech_sheet_entry.subtitle')}
      </p>

      {error && (
        <div role="alert" style={{
          marginBottom: 12, padding: 12, borderRadius: 'var(--r-ctrl)',
          border: '1px solid var(--err)', background: 'var(--err-bg)', color: 'var(--err)',
          fontSize: 'var(--fs-body)',
        }}>
          <i className="ti ti-alert-circle" aria-hidden="true" style={{ marginRight: 6, fontSize: 14, color: 'currentColor' }} />
          {error}
        </div>
      )}

      {consultaModel && (
        <div role="alert" style={{
          marginBottom: 12, padding: 12, borderRadius: 'var(--r-ctrl)',
          border: '1px solid var(--gold-border)', background: 'var(--panel)',
          fontSize: 'var(--fs-body)',
        }}>
          <div style={{ marginBottom: 8 }}>
            <i className="ti ti-lock" aria-hidden="true" style={{ marginRight: 6, fontSize: 14, color: 'var(--text-soft)' }} />
            {t('tech_sheet_entry.not_allowed', { codi: consultaModel.codi_intern })}
          </div>
          <button
            type="button"
            onClick={() => obrirConsulta(consultaModel.id)}
            style={botoSec}>
            <i className="ti ti-eye" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
            {t('tech_sheet_entry.open_readonly')}
          </button>
        </div>
      )}

      <AssetNavigator
        mode="models"
        inline
        nav={nav}
        onNav={setNav}
        onPick={obrir}
        actionLabel={busyId ? t('app.loading') : t('tech_sheet_entry.open')}
      />
    </div>
    </>
  )
}
