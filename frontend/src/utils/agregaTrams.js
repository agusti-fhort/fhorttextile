/**
 * F2.6 · §S-3 — AGREGACIÓ DE TRAMS SOBRE ELS CAMPS QUE EL SERVIDOR EMET DE DEBÒ.
 *
 * La pàgina `/temps` llegia `data_inici`, `data_fi` i `created_at`. Cap dels tres existeix:
 * `TimerEntrada` té `inici`, `fi`, `minuts`, `actiu`, `last_heartbeat` i (des de F1.7) `origen`,
 * i `created_at` no és ni tan sols una columna de la taula. Conseqüència mesurada: `''` mai és
 * igual a la data d'avui, de manera que **la llista del dia i el gràfic de set dies eren sempre
 * buits** — la pàgina ensenyava zero a algú que havia treballat vuit hores.
 *
 * Les tres lleis que aquest mòdul respecta, totes heretades del backend:
 *
 *   1. **El dia és el de l'INICI del tram.** Un tram que creua mitjanit compta al dia que va
 *      començar, que és el que fa el `TRAMS_SANS` del servidor i el que espera qui el llegeix.
 *   2. **`minuts` mana quan hi és.** El servidor l'ha calculat amb `floor(segons/60)` en tancar;
 *      recalcular-lo al client donaria una xifra que no quadraria amb l'albarà.
 *   3. **Els trams desbocats no es compten.** Mateix sostre que `MAX_MINUTS_TRAM`: un tram de
 *      més d'un dia és una fuita, no una jornada llarga.
 */

export const MAX_MINUTS_TRAM = 24 * 60

/** El dia (YYYY-MM-DD) LOCAL d'un tram. Local i no UTC: qui mira la pàgina viu en un fus. */
export function diaDelTram(tram) {
  if (!tram?.inici) return null
  const d = new Date(tram.inici)
  if (Number.isNaN(d.getTime())) return null
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/**
 * Minuts que aporta un tram. `ara` s'injecta per fer provable el cas del tram obert.
 * Un tram obert compta el que porta corregut: la pàgina ha de dir la veritat d'ara mateix.
 */
export function minutsDelTram(tram, ara = Date.now()) {
  if (!tram?.inici) return 0
  if (tram.minuts != null) {
    return tram.minuts > MAX_MINUTS_TRAM ? 0 : tram.minuts   // llei 3
  }
  const fi = tram.fi ? new Date(tram.fi).getTime() : ara
  const mins = Math.max(0, Math.floor((fi - new Date(tram.inici).getTime()) / 60000))
  return mins > MAX_MINUTS_TRAM ? 0 : mins
}

/** El tram obert del tècnic, o null. `fi == null` és la definició; `actiu` n'és el mirall. */
export function tramObert(trams) {
  return (trams || []).find(x => x.fi == null && x.actiu !== false) || null
}

/** Els trams TANCATS d'un dia concret, ordenats per hora d'inici. */
export function tramsDelDia(trams, dia) {
  return (trams || [])
    .filter(x => x.fi != null && diaDelTram(x) === dia)
    .sort((a, b) => String(a.inici).localeCompare(String(b.inici)))
}

/**
 * Els darrers `n` dies amb els seus minuts, del més antic al més recent.
 * `avui` s'injecta (Date) per fer-ho provable sense congelar el rellotge.
 */
export function darrersDies(trams, n = 7, avui = new Date(), ara = Date.now()) {
  const perDia = new Map()
  for (const tram of trams || []) {
    const dia = diaDelTram(tram)
    if (!dia) continue
    perDia.set(dia, (perDia.get(dia) || 0) + minutsDelTram(tram, ara))
  }
  const p = x => String(x).padStart(2, '0')
  const dies = []
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(avui.getFullYear(), avui.getMonth(), avui.getDate() - i)
    const clau = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
    dies.push({ clau, data: d, minuts: perDia.get(clau) || 0 })
  }
  return dies
}

/** `1h 05m` · `12m`. Sense segons: això és un resum, no un cronòmetre. */
export function formataMinuts(minuts) {
  const m = Math.max(0, Math.floor(minuts || 0))
  const h = Math.floor(m / 60)
  return h > 0 ? `${h}h ${String(m % 60).padStart(2, '0')}m` : `${m % 60}m`
}

/** `09:30` en hora LOCAL. La franja d'un tram es llegeix en l'hora de qui la mira. */
export function horaLocal(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const p = x => String(x).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}
