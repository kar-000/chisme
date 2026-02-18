import api from './api'

export const editMessage = (id, content) =>
  api.put(`/messages/${id}`, { content })

export const deleteMessage = (id) => api.delete(`/messages/${id}`)

export const addReaction = (messageId, emoji) =>
  api.post(`/messages/${messageId}/reactions`, { emoji })

export const removeReaction = (messageId, emoji) =>
  api.delete(`/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`)
