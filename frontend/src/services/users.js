import api from './api'

export const getUser = (userId) => api.get(`/users/${userId}`)

export const searchUsers = (q, limit = 20) =>
  api.get('/users/search', { params: { q, limit } })

export const updateMe = (updates) => api.patch('/users/me', updates)
