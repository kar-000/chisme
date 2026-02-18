import { create } from 'zustand'
import { login as apiLogin, register as apiRegister, getMe } from '../services/auth'

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
      localStorage.removeItem('token')
      set({ user: null, token: null })
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null })
  },

  clearError: () => set({ error: null }),
}))

export default useAuthStore
