import api from './api'

export const listDMs = () => api.get('/dms')
export const getOrCreateDM = (otherUserId) => api.post(`/dms?other_user_id=${otherUserId}`)
export const getDMMessages = (dmId, params) => api.get(`/dms/${dmId}/messages`, { params })
export const sendDMMessage = (dmId, content, replyToId = null) =>
  api.post(`/dms/${dmId}/messages`, {
    content,
    ...(replyToId != null && { reply_to_id: replyToId }),
  })
