import api from './api'

export const getUser = (userId) => api.get(`/users/${userId}`)

export const updateMe = (updates) => api.patch('/users/me', updates)

export const uploadAvatar = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/users/me/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
