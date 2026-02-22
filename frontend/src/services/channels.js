import api from './api'

export const listChannels = (serverId, params) =>
  api.get(`/servers/${serverId}/channels`, { params })
export const createChannel = (serverId, name, description) =>
  api.post(`/servers/${serverId}/channels`, { name, description })
export const getChannel = (serverId, channelId) =>
  api.get(`/servers/${serverId}/channels/${channelId}`)
export const deleteChannel = (serverId, channelId) =>
  api.delete(`/servers/${serverId}/channels/${channelId}`)
export const getMessages = (serverId, channelId, params) =>
  api.get(`/servers/${serverId}/channels/${channelId}/messages`, { params })
export const sendMessage = (serverId, channelId, content, attachmentIds = [], replyToId = null) =>
  api.post(`/servers/${serverId}/channels/${channelId}/messages`, {
    content,
    attachment_ids: attachmentIds,
    ...(replyToId != null && { reply_to_id: replyToId }),
  })
export const markChannelRead = (serverId, channelId) =>
  api.post(`/servers/${serverId}/channels/${channelId}/read`)
export const getChannelMembers = (serverId, channelId, q) =>
  api.get(`/servers/${serverId}/channels/${channelId}/members`, {
    params: q ? { q } : {},
  })
