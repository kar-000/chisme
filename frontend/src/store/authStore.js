import { create } from 'zustand'
import { login as apiLogin, register as apiRegister, getMe, revokeToken } from '../services/auth'

const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token') || null,
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiLogin(username, password)
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      set({ user: data.user, token: data.access_token, loading: false })
    } catch (err) {
      set({ error: err.response?.data?.detail ?? 'Login failed', loading: false })
    }
  },

  register: async (username, email, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiRegister(username, email, password)
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      set({ user: data.user, token: data.access_token, loading: false })
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : (detail ?? 'Registration failed')
      set({ error: msg, loading: false })
    }
  },

  loadUser: async () => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      const { data } = await getMe()
      set({ user: data, token })
    } catch {
      // getMe() returning an error here means even the silent refresh failed
      // (api.js interceptor already attempted it). Clear everything.
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      set({ user: null, token: null })
    }
  },

  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        await revokeToken(refreshToken)
      } catch {
        // best-effort — clear local state regardless
      }
    }
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    set({ user: null, token: null })
  },

  clearError: () => set({ error: null }),

  setUser: (user) => set({ user }),
}))

export default useAuthStore
