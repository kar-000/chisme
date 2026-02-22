import api from './api'

export const listServers = () => api.get('/servers')
export const createServer = (data) => api.post('/servers', data)
export const getServer = (serverId) => api.get(`/servers/${serverId}`)
export const updateServer = (serverId, data) => api.patch(`/servers/${serverId}`, data)
export const deleteServer = (serverId) => api.delete(`/servers/${serverId}`)

export const listMembers = (serverId) => api.get(`/servers/${serverId}/members`)
export const removeMember = (serverId, userId) =>
  api.delete(`/servers/${serverId}/members/${userId}`)
export const updateMemberRole = (serverId, userId, role) =>
  api.patch(`/servers/${serverId}/members/${userId}/role`, { role })
export const transferOwnership = (serverId, newOwnerId) =>
  api.post(`/servers/${serverId}/transfer-ownership`, { new_owner_id: newOwnerId })

export const createInvite = (serverId, options = {}) =>
  api.post(`/servers/${serverId}/invites`, options)
export const revokeInvite = (serverId, code) =>
  api.delete(`/servers/${serverId}/invites/${code}`)

export const previewInvite = (code) => api.get(`/invites/${code}`)
export const redeemInvite = (code) => api.post(`/invites/${code}/redeem`)
