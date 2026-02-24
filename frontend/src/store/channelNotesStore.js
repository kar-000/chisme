import { create } from 'zustand'
import { getChannelNotes, saveChannelNotes, getChannelNotesHistory } from '../services/channelNotes'

const useChannelNotesStore = create((set, get) => ({
  // { [channelId]: { content, version, updated_by, updated_by_username, updated_at } }
  cache: {},
  loadingChannels: new Set(),

  fetchNotes: async (channelId) => {
    if (get().loadingChannels.has(channelId)) return
    set((s) => ({ loadingChannels: new Set([...s.loadingChannels, channelId]) }))
    try {
      const { data } = await getChannelNotes(channelId)
      set((s) => ({
        cache: { ...s.cache, [channelId]: data ?? null },
        loadingChannels: new Set([...s.loadingChannels].filter((id) => id !== channelId)),
      }))
    } catch {
      set((s) => ({
        loadingChannels: new Set([...s.loadingChannels].filter((id) => id !== channelId)),
      }))
    }
  },

  saveNotes: async (channelId, content, baseVersion) => {
    const { data } = await saveChannelNotes(channelId, content, baseVersion)
    set((s) => ({ cache: { ...s.cache, [channelId]: data } }))
    return data
  },

  // Called from WebSocket — update cache without an API round-trip
  applyWsUpdate: (channelId, wsData) => {
    set((s) => ({
      cache: {
        ...s.cache,
        [channelId]: {
          ...(s.cache[channelId] ?? {}),
          content: wsData.content,
          version: wsData.version,
          updated_by_username: wsData.updated_by,
        },
      },
    }))
  },

  fetchHistory: async (channelId) => {
    const { data } = await getChannelNotesHistory(channelId)
    return data
  },
}))

export default useChannelNotesStore
