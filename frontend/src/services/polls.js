import api from './api'

export const createPoll = (data) => api.post('/polls', data)
export const getPoll = (pollId) => api.get(`/polls/${pollId}`)
export const castVote = (pollId, optionIds) =>
  api.post(`/polls/${pollId}/vote`, { option_ids: optionIds })
export const removeVote = (pollId) => api.delete(`/polls/${pollId}/vote`)
