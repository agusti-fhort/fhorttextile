import { create } from 'zustand'
import client from '../api/client'
import { me as meApi } from '../api/endpoints'

const useAuthStore = create((set, get) => ({
  token: null,
  user: null,            // { id, username, nom_complet, rol_nom, color_avatar, capabilities }
  isAuthenticated: false,

  initAuth: () => {
    const token = localStorage.getItem('access_token')
    if (token) {
      set({ token, isAuthenticated: true })
      get().fetchMe()    // carrega user + capabilities en sessions ja autenticades
    }
  },

  login: async (username, password) => {
    const res = await client.post('/api/token/', { username, password })
    const { access, refresh } = res.data
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ token: access, isAuthenticated: true })
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
      })
      return data
    } catch (err) {
      if (err?.response?.status === 401) get().logout()
      return null
    }
  },

  // Helper cosmètic: el backend ja enforça; això només mostra/amaga accions a la UI.
  hasCapability: (cap) => get().user?.capabilities?.includes(cap) ?? false,

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ token: null, user: null, isAuthenticated: false })
    window.location.href = '/login'
  },
}))

export default useAuthStore
