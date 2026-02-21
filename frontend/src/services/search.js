import api from './api'

export const searchMessages = (q, channelId, limit = 50) => {
  const params = new URLSearchParams({ q, limit })
  if (channelId) params.set('channel_id', channelId)
  return api.get(`/search/messages?${params}`)
}
