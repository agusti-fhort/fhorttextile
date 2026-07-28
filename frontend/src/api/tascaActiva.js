import { apiBaseURL } from './base'
import { creaPausador } from './tascaActivaCore'

/**
 * K6 · CAPA FRONTEND — sessió morta ⇒ tasca en pausa (best-effort).
 *
 * Qui sap quina tasca duc En curs és `GuardTascaOblidada`, que ja ho sondeja cada minut per
 * armar el seu llindar. Aquí només se'n desa l'id perquè el camí de tancament de sessió el
 * pugui llegir SENSE muntar un segon sondeig ni un segon concepte de «tasca activa».
 *
 * És una variable de mòdul i no estat de React a posta: qui ho ha de llegir (`sessio.js`,
 * `store/auth.js`) no és un component i no pot subscriure's a res.
 *
 * LA PARADOXA DEL TOKEN: quan la sessió mor perquè el refresh ha caducat, aquesta crida surt
 * amb un access token que probablement TAMBÉ és mort — i fallarà amb el mateix 401. És
 * acceptat: aquesta capa és un intent, no una garantia. La garantia és el cron
 * `pausa_tasques_oblidades` del servidor. Per això el fracàs s'empassa en silenci i mai
 * bloqueja la redirecció.
 *
 * Al logout VOLUNTARI el token és viu i la pausa sí que és fiable: allà s'espera.
 *
 * La DECISIÓ viu a `tascaActivaCore.js` (pur, provable); aquí només hi ha el cablatge.
 */
const pausador = creaPausador({
  llegeixToken: () => {
    try { return localStorage.getItem('access_token') } catch { return null }   // mode privat
  },
  envia: (id, token) => fetch(`${apiBaseURL}/api/v1/model-task-items/${id}/transition/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    // Sense marca `auto`: si va pel logout voluntari és un gest de l'usuari. La pausa del
    // cron (que sí signa com a guard, amb `cron_40min`) és l'altra capa i té el seu camí.
    body: JSON.stringify({ to_status: 'Paused' }),
    // `keepalive` perquè la petició sobrevisqui a la navegació cap a /login: sense això, el
    // `window.location.href` immediatament posterior l'avortaria i la capa 1 no serviria de
    // res justament en el cas per al qual existeix.
    keepalive: true,
  }).then(r => r.ok),
  // Va amb `fetch` cru i NO amb `authFetch`: aquí un 401 no s'ha de refrescar (la sessió és
  // morta, o s'està tancant a posta) i entrar al camí de refresh seria recursió.
})

export const recordaTascaActiva = taskId => pausador.recorda(taskId)
export const tascaActivaId = () => pausador.id
export const pausaTascaActiva = () => pausador.pausa()
