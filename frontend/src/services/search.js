import api from './api'

export const searchMessages = (q, channelId, filters = {}, limit = 50) => {
  const params = new URLSearchParams({ limit })
  if (q) params.set('q', q)
  if (channelId) params.set('channel_id', channelId)
  if (filters.from_user) params.set('from_user', filters.from_user)
  if (filters.after) params.set('after', filters.after)
  if (filters.before) params.set('before', filters.before)
  if (filters.has_link) params.set('has_link', 'true')
  if (filters.has_file) params.set('has_file', 'true')
  return api.get(`/search/messages?${params}`)
}
