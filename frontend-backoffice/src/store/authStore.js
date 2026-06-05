import { create } from 'zustand'

// Clau de localStorage dedicada al backoffice (no col·lisiona amb el producte).
const TOKEN_KEY = 'bo_access_token'

const useAuthStore = create((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY) || null,
  user: null,   // perfil retornat per /auth/me/
  rol: null,    // rol de l'usuari autenticat

  // Desa (o actualitza parcialment) les dades d'autenticació. Persisteix el
  // token a localStorage perquè la sessió sobrevisqui a recàrregues.
  setAuth: ({ user, token, rol } = {}) => {
    if (token !== undefined) {
      if (token) localStorage.setItem(TOKEN_KEY, token)
      else localStorage.removeItem(TOKEN_KEY)
    }
    set((state) => ({
      token: token !== undefined ? token : state.token,
      user: user !== undefined ? user : state.user,
      rol: rol !== undefined ? rol : state.rol,
    }))
  },

  clearAuth: () => {
    localStorage.removeItem(TOKEN_KEY)
    set({ token: null, user: null, rol: null })
  },

  isAuthenticated: () => !!get().token,
}))

export const TOKEN_STORAGE_KEY = TOKEN_KEY
export default useAuthStore
