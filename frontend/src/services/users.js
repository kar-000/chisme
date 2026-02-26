import api from './api'

export const getUser = (userId) => api.get(`/users/${userId}`)
export const getUserByUsername = (username) => api.get(`/users/by-username/${username}`)

export const searchUsers = (q, limit = 20) =>
  api.get('/users/search', { params: { q, limit } })

export const updateMe = (updates) => api.patch('/users/me', updates)

export const uploadAvatar = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/users/me/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getQuietHours = () => api.get('/users/me/quiet-hours')
export const updateQuietHours = (payload) => api.patch('/users/me/quiet-hours', payload)

export const setNickname = (serverId, nickname) =>
  api.patch(`/users/me/servers/${serverId}/nickname`, { nickname })

export const clearNickname = (serverId) =>
  api.delete(`/users/me/servers/${serverId}/nickname`)
