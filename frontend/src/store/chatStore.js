import { create } from 'zustand'
import { listChannels, createChannel, getMessages, sendMessage } from '../services/channels'
import { addReaction, removeReaction, editMessage, deleteMessage } from '../services/messages'

const useChatStore = create((set, get) => ({
  channels: [],
  activeChannelId: null,
  messages: [],          // messages for active channel
  messagesTotal: 0,
  loadingMessages: false,
  typingUsers: [],       // usernames currently typing

  /* ── Channels ─────────────────────────────────────────────────── */
  fetchChannels: async () => {
    const { data } = await listChannels({ limit: 100 })
    set({ channels: data })
    // Auto-select general or first channel
    if (!get().activeChannelId && data.length > 0) {
      const general = data.find((c) => c.name === 'general') ?? data[0]
      get().selectChannel(general.id)
    }
  },

  createChannel: async (name, description) => {
    const { data } = await createChannel(name, description)
    set((s) => ({ channels: [...s.channels, data] }))
    get().selectChannel(data.id)
  },

  selectChannel: async (channelId) => {
    set({ activeChannelId: channelId, messages: [], messagesTotal: 0, typingUsers: [] })
    get().fetchMessages(channelId)
  },

  /* ── Messages ─────────────────────────────────────────────────── */
  fetchMessages: async (channelId) => {
    set({ loadingMessages: true })
    try {
      const { data } = await getMessages(channelId, { limit: 50 })
      // API returns newest-first; reverse for display
      set({ messages: [...data.messages].reverse(), messagesTotal: data.total, loadingMessages: false })
    } catch {
      set({ loadingMessages: false })
    }
  },

  sendMessage: async (content) => {
    const { activeChannelId } = get()
    if (!activeChannelId) return
    await sendMessage(activeChannelId, content)
    // WS broadcast will add the message; fallback refresh if WS is absent
  },

  // Called by WebSocket when a new message arrives
  appendMessage: (msg) => {
    set((s) => {
      if (s.messages.find((m) => m.id === msg.id)) return s
      return { messages: [...s.messages, msg] }
    })
  },

  updateMessage: (updated) => {
    set((s) => ({
      messages: s.messages.map((m) => (m.id === updated.id ? updated : m)),
    }))
  },

  removeMessage: (id) => {
    set((s) => ({ messages: s.messages.filter((m) => m.id !== id) }))
  },

  /* ── Reactions ────────────────────────────────────────────────── */
  addReaction: async (messageId, emoji) => {
    const { data } = await addReaction(messageId, emoji)
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === messageId
          ? { ...m, reactions: [...(m.reactions ?? []), data] }
          : m
      ),
    }))
  },

  removeReaction: async (messageId, emoji, userId) => {
    await removeReaction(messageId, emoji)
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === messageId
          ? {
              ...m,
              reactions: (m.reactions ?? []).filter(
                (r) => !(r.emoji === emoji && r.user_id === userId)
              ),
            }
          : m
      ),
    }))
  },

  /* ── Edit / delete ────────────────────────────────────────────── */
  editMessage: async (id, content) => {
    const { data } = await editMessage(id, content)
    get().updateMessage(data)
  },

  deleteMessage: async (id) => {
    await deleteMessage(id)
    get().removeMessage(id)
  },

  /* ── Typing ───────────────────────────────────────────────────── */
  setTypingUsers: (updater) =>
    typeof updater === 'function'
      ? set((s) => ({ typingUsers: updater(s.typingUsers) }))
      : set({ typingUsers: updater }),
}))

export default useChatStore
