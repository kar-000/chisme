import api from './api'

export const getUser = (userId) => api.get(`/users/${userId}`)

export const updateMe = (updates) => api.patch('/users/me', updates)
