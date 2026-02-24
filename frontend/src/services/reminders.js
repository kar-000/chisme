import api from './api'

export const listReminders = () => api.get('/reminders')
export const createReminder = (messageId, remindAt) =>
  api.post('/reminders', { message_id: messageId, remind_at: remindAt })
export const cancelReminder = (reminderId) => api.delete(`/reminders/${reminderId}`)
