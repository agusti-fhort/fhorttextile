import { create } from 'zustand'
import client from '../api/client'
import { authCentral, me as meApi } from '../api/endpoints'

/**
 * L'estat de l'auth té TRES valors, no dos (D10).
 *
 * `isAuthenticated` sol no en té prou: un booleà no sap distingir «no hi ha sessió» de
 * «encara no he mirat si n'hi ha». I com que arrenca a `false`, qui el llegís abans que
 * `initAuth` hagués corregut entenia «no hi ha sessió» — i rebotava a /login algú que la
 * tenia perfectament vàlida. Era el que passava a cada F5 sobre una ruta protegida.
 *
 * Amb tres valors, el moment de no-saber és un estat i es pot esperar, en comptes de ser un
 * «no» disfressat.
 */
export const AUTH_DESCONEGUT = 'desconegut'   // encara no s'ha mirat el localStorage
export const AUTH_VALID = 'valid'
export const AUTH_INVALID = 'invalid'

const useAuthStore = create((set, get) => ({
  token: null,
  user: null,            // { id, username, nom_complet, rol_nom, color_avatar, capabilities }
  // P7 (Federació v2) — la CASA, no la persona: { nom, codi_tenant, tipologia }. Va a part de
  // `user` a posta: no és un atribut de qui ha entrat sinó d'on ha entrat, i sobreviu igual a
  // qualsevol usuari del mateix tenant. Null mentre /me no ha respost (i al schema public).
  tenant: null,
  isAuthenticated: false,
  estatAuth: AUTH_DESCONEGUT,

  initAuth: () => {
    // ATERRATGE AMB CODI (login únic, F2): arribar a /entrar amb un ?code= vol dir que aquí
    // COMENÇA una sessió, no que se n'estigui reprenent una. El que hi hagués al localStorage
    // d'aquest origen ja no compta i, sobretot, no pot competir-hi: si `initAuth` el donés per
    // bo, `fetchMe()` sortiria amb un token ranci, cauria amb 401 i el camí de refresh acabaria
    // a `tancaSessio()` — que esborra els DOS tokens, inclosos els que el bescanvi acaba
    // d'escriure, i expulsa a /login. I com que el codi és d'un sol ús, ja s'hauria cremat: no
    // hi hauria reintent possible. L'escenari no és marginal: és l'estat de tothom just després
    // del deploy de F0, que invalida tots els tokens anteriors.
    const arribaAmbCodi = window.location.pathname === '/entrar'
      && new URLSearchParams(window.location.search).has('code')
    if (arribaAmbCodi) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ token: null, user: null, tenant: null, isAuthenticated: false, estatAuth: AUTH_INVALID })
      return
    }

    const token = localStorage.getItem('access_token')
    if (token) {
      set({ token, isAuthenticated: true, estatAuth: AUTH_VALID })
      get().fetchMe()    // carrega user + capabilities en sessions ja autenticades
    } else {
      // Mirat, i no hi ha res: ara sí que és un «no».
      set({ estatAuth: AUTH_INVALID })
    }
  },

  login: async (username, password) => {
    const res = await client.post('/api/token/', { username, password })
    const { access, refresh } = res.data
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ token: access, isAuthenticated: true, estatAuth: AUTH_VALID })
    await get().fetchMe()
    return res.data
  },

  // Login únic (F2): la sessió no neix d'unes credencials sinó d'un codi d'un sol ús que la
  // porta central ha emès per a AQUEST tenant. A partir d'aquí tot és idèntic al login de
  // sempre — el mateix parell de tokens, el mateix localStorage, el mateix fetchMe. És
  // deliberat que passi per aquí i no per la pantalla: una segona manera de desar la sessió
  // seria una segona manera d'oblidar-se de netejar-la.
  entraAmbCodi: async (code) => {
    const res = await authCentral.bescanvia(code)
    const { access, refresh } = res.data
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ token: access, isAuthenticated: true, estatAuth: AUTH_VALID })
    await get().fetchMe()
    return res.data
  },

  // Carrega el perfil de l'usuari autenticat (me/) i en desa les capacitats.
  // Font única de `capabilities` per a tot el front (la UI les usa per amagar/deshabilitar).
  fetchMe: async () => {
    try {
      const { data } = await meApi.get()
      set({
        user: {
          id: data.id,
          username: data.username,
          nom_complet: data.nom_complet,
          rol_nom: data.rol_nom,
          color_avatar: data.color_avatar,
          capabilities: data.capabilities || [],
        },
        tenant: data.tenant || null,
      })
      return data
    } catch (err) {
      if (err?.response?.status === 401) get().logout()
      return null
    }
  },

  // Helper cosmètic: el backend ja enforça; això només mostra/amaga accions a la UI.
  hasCapability: (cap) => get().user?.capabilities?.includes(cap) ?? false,

  // P7 — la naturalesa de la casa. Derivats, mai desats: una segona còpia de `tipologia`
  // seria una segona cosa a mantenir sincronitzada. Tots dos són FALSE mentre /me no ha
  // arribat, que és el que toca: cap superfície del Brand s'ha de pintar per suposició.
  isBrand: () => get().tenant?.tipologia === 'marca',
  isStudio: () => get().tenant?.tipologia === 'estudi',

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ token: null, user: null, tenant: null, isAuthenticated: false, estatAuth: AUTH_INVALID })
    window.location.href = '/login'
  },
}))

export default useAuthStore
