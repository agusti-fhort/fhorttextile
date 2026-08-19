/**
 * F2.5 · D-2 — VALIDACIÓ DEL TEMPS DECLARAT (la decisió; el formulari viu al JSX).
 *
 * Una tasca `Externa-lliure` —patró a mà, revisió de disseny, aclariments— es fa FORA de l'eina:
 * no hi ha cap escriptura que batre i el rellotge no hi arriba mai. Aquest és l'únic camí pel qual
 * aquell temps entra al sistema.
 *
 * El guard dur (només Externa-lliure, sostre de 24 h) ja és al backend i hi ha de seguir sent:
 * això valida ABANS d'enviar perquè l'usuari no hagi d'esperar un 400 per saber que s'ha deixat
 * un camp, no per substituir-lo.
 */

export const MAX_MINUTS = 24 * 60      // mateix sostre que `MAX_MINUTS_TRAM` del backend

export const MODE_DURADA = 'durada'
export const MODE_FRANJA = 'franja'

/**
 * Valida el formulari i construeix el cos de la petició.
 *
 * @returns {{ok: true, cos: object} | {ok: false, error: string}}
 *   `error` és una CLAU d'i18n, mai text: qui pinta decideix l'idioma.
 */
export function validaTempsDeclarat({ mode, minuts, inici, fi }, ara = Date.now()) {
  if (mode === MODE_DURADA) {
    const n = Number(minuts)
    if (!minuts || !Number.isFinite(n)) return { ok: false, error: 'temps_declarat.err_minuts' }
    if (!Number.isInteger(n)) return { ok: false, error: 'temps_declarat.err_enter' }
    if (n <= 0) return { ok: false, error: 'temps_declarat.err_zero' }
    if (n > MAX_MINUTS) return { ok: false, error: 'temps_declarat.err_sostre' }
    return { ok: true, cos: { minuts: n } }
  }

  if (mode === MODE_FRANJA) {
    if (!inici || !fi) return { ok: false, error: 'temps_declarat.err_franja_incompleta' }
    const t0 = new Date(inici).getTime()
    const t1 = new Date(fi).getTime()
    if (!Number.isFinite(t0) || !Number.isFinite(t1)) {
      return { ok: false, error: 'temps_declarat.err_data' }
    }
    if (t1 <= t0) return { ok: false, error: 'temps_declarat.err_invertida' }
    const mins = Math.floor((t1 - t0) / 60000)
    if (mins <= 0) return { ok: false, error: 'temps_declarat.err_zero' }
    if (mins > MAX_MINUTS) return { ok: false, error: 'temps_declarat.err_sostre' }
    // Declarar feina del futur no és declarar: és equivocar-se de camp.
    if (t1 > ara) return { ok: false, error: 'temps_declarat.err_futur' }
    return { ok: true, cos: { inici: new Date(t0).toISOString(), fi: new Date(t1).toISOString() } }
  }

  return { ok: false, error: 'temps_declarat.err_mode' }
}

/** El formulari només existeix per a les tasques externes: les internes es mesuren soles. */
export function admetTempsDeclarat(tasca) {
  return Boolean(tasca?.tipus_extern)
}
