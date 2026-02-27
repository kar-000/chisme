import { create } from 'zustand'

const useNotificationStore = create((set, get) => ({
  // server_id (number) -> 'mention' | 'message'
  serverNotifications: {},

  addServerNotification(serverId, type) {
    const current = get().serverNotifications[serverId]
    // Never downgrade from 'mention' to 'message'
    if (current === 'mention') return
    set((state) => ({
      serverNotifications: { ...state.serverNotifications, [serverId]: type },
    }))
  },

  clearServerNotification(serverId) {
    set((state) => {
      const next = { ...state.serverNotifications }
      delete next[serverId]
      return { serverNotifications: next }
    })
  },

  hasNotification(serverId) {
    return serverId in get().serverNotifications
  },

  getNotificationType(serverId) {
    return get().serverNotifications[serverId] ?? null
  },
}))

export default useNotificationStore
