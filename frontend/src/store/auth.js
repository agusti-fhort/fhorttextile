import { create } from 'zustand'
import client from '../api/client'

const useAuthStore = create((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,

  initAuth: () => {
    const token = localStorage.getItem('access_token')
    if (token) set({ token, isAuthenticated: true })
  },

  login: async (username, password) => {
    const res = await client.post('/api/token/', { username, password })
    const { access, refresh } = res.data
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ token: access, isAuthenticated: true })
    return res.data
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ token: null, user: null, isAuthenticated: false })
    window.location.href = '/login'
  },
}))

export default useAuthStore
