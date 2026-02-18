import api from './api'

export const register = (username, email, password) =>
  api.post('/auth/register', { username, email, password })

export const login = (username, password) =>
  api.post('/auth/login', { username, password })

export const getMe = () => api.get('/auth/me')
