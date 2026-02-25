import api from './api'

export const getChannelNotes = (channelId) => api.get(`/channels/${channelId}/notes`)
export const saveChannelNotes = (channelId, content, baseVersion) =>
  api.put(`/channels/${channelId}/notes`, { content, base_version: baseVersion })
export const getChannelNotesHistory = (channelId) =>
  api.get(`/channels/${channelId}/notes/history`)
