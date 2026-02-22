import { create } from 'zustand'
import { listServers } from '../services/servers'

// Lazy imports to avoid circular dependency at module load time.
// chatStore and useWebSocket are imported inside actions that need them.
const getChatStore = () => import('./chatStore').then((m) => m.default.getState())

const useServerStore = create((set, get) => ({
  servers: [],
  activeServerId: null,
  loadingServers: false,

  /* ── Fetch ─────────────────────────────────────────────────────── */
  fetchServers: async () => {
    set({ loadingServers: true })
    try {
      const { data } = await listServers()
      set({ servers: data, loadingServers: false })

      // Auto-select the first server if none is active yet
      if (!get().activeServerId && data.length > 0) {
        get().setActiveServer(data[0].id)
      }
    } catch {
      set({ loadingServers: false })
    }
  },

  /* ── Activate ──────────────────────────────────────────────────── */
  setActiveServer: async (serverId) => {
    set({ activeServerId: serverId })

    // Reload the channel list for the new server
    const chatState = (await getChatStore())
    chatState.fetchChannels(serverId)
  },

  /* ── Mutations ─────────────────────────────────────────────────── */
  addServer: (server) =>
    set((s) => ({ servers: [...s.servers, server] })),

  updateServer: (updated) =>
    set((s) => ({
      servers: s.servers.map((sv) => (sv.id === updated.id ? { ...sv, ...updated } : sv)),
    })),

  removeServer: (serverId) =>
    set((s) => {
      const remaining = s.servers.filter((sv) => sv.id !== serverId)
      return {
        servers: remaining,
        activeServerId:
          s.activeServerId === serverId
            ? (remaining[0]?.id ?? null)
            : s.activeServerId,
      }
    }),
}))

export default useServerStore
