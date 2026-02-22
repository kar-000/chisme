import api from './api'

export const listChannels = (params) => api.get('/channels', { params })
export const createChannel = (name, description) =>
  api.post('/channels', { name, description })
export const getChannel = (id) => api.get(`/channels/${id}`)
export const getMessages = (channelId, params) =>
  api.get(`/channels/${channelId}/messages`, { params })
export const sendMessage = (channelId, content, attachmentIds = [], replyToId = null) =>
  api.post(`/channels/${channelId}/messages`, {
    content,
    attachment_ids: attachmentIds,
    ...(replyToId != null && { reply_to_id: replyToId }),
  })
export const markChannelRead = (channelId) => api.post(`/channels/${channelId}/read`)
export const getChannelMembers = (channelId, q) =>
  api.get(`/channels/${channelId}/members`, { params: q ? { q } : {} })
