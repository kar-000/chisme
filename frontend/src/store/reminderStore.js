import { create } from 'zustand'
import { listReminders, createReminder, cancelReminder } from '../services/reminders'

const useReminderStore = create((set, get) => ({
  reminders: [],
  loading: false,

  fetchReminders: async () => {
    set({ loading: true })
    try {
      const { data } = await listReminders()
      set({ reminders: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  addReminder: async (messageId, remindAt) => {
    const { data } = await createReminder(messageId, remindAt)
    set((s) => ({ reminders: [...s.reminders, data].sort((a, b) => new Date(a.remind_at) - new Date(b.remind_at)) }))
    return data
  },

  removeReminder: async (reminderId) => {
    await cancelReminder(reminderId)
    set((s) => ({ reminders: s.reminders.filter((r) => r.id !== reminderId) }))
  },

  // Called when a reminder_due WebSocket event arrives — removes from list
  // (it's been delivered) and returns the payload for toast display.
  markDelivered: (reminderId) => {
    const reminder = get().reminders.find((r) => r.id === reminderId)
    set((s) => ({ reminders: s.reminders.filter((r) => r.id !== reminderId) }))
    return reminder
  },
}))

export default useReminderStore
