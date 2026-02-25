import api from './api'

export const getKeywords = () => api.get('/users/me/keywords')
export const addKeyword = (keyword) => api.post('/users/me/keywords', { keyword })
export const deleteKeyword = (id) => api.delete(`/users/me/keywords/${id}`)
