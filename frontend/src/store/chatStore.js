import { create } from 'zustand'
import { listChannels, createChannel, getMessages, sendMessage, markChannelRead } from '../services/channels'
import { addReaction, removeReaction, editMessage, deleteMessage } from '../services/messages'

let _nextTempId = 1

const useChatStore = create((set, get) => ({
  channels: [],
  activeChannelId: null,
  messages: [],          // messages for active channel
  messagesTotal: 0,
  loadingMessages: false,
  typingUsers: [],       // usernames currently typing

  // Pending attachments: [{ tempId, file, progress, id, url, error }]
  pendingAttachments: [],

  // Quote-reply: the message being replied to (or null)
  replyingTo: null,

  // Unread counts: { [channelId]: number }
  unreadCounts: {},

  /* ── Channels ─────────────────────────────────────────────────── */
  fetchChannels: async (serverId) => {
    if (!serverId) return
    const { data } = await listChannels(serverId, { limit: 100 })
    const unreadCounts = {}
    data.forEach((c) => { unreadCounts[c.id] = c.unread_count ?? 0 })
    set({ channels: data, unreadCounts, activeChannelId: null })
    if (data.length > 0) {
      const general = data.find((c) => c.name === 'general') ?? data[0]
      get().selectChannel(serverId, general.id)
    }
  },

  createChannel: async (serverId, name, description) => {
    const { data } = await createChannel(serverId, name, description)
    set((s) => ({ channels: [...s.channels, data] }))
    get().selectChannel(serverId, data.id)
  },

  selectChannel: async (serverId, channelId) => {
    set((s) => ({
      activeChannelId: channelId,
      messages: [],
      messagesTotal: 0,
      typingUsers: [],
      pendingAttachments: [],
      replyingTo: null,
      unreadCounts: { ...s.unreadCounts, [channelId]: 0 },
    }))
    get().fetchMessages(serverId, channelId)
    markChannelRead(serverId, channelId).catch(() => {})
  },

  clearActiveChannel: () => {
    set({
      activeChannelId: null,
      messages: [],
      messagesTotal: 0,
      typingUsers: [],
      pendingAttachments: [],
      replyingTo: null,
    })
  },

  /* ── Messages ─────────────────────────────────────────────────── */
  fetchMessages: async (serverId, channelId) => {
    set({ loadingMessages: true })
    try {
      const { data } = await getMessages(serverId, channelId, { limit: 50 })
      set({
        messages: [...data.messages].reverse(),
        messagesTotal: data.total,
        loadingMessages: false,
      })
    } catch {
      set({ loadingMessages: false })
    }
  },

  sendMessage: async (serverId, content, attachmentIds = []) => {
    const { activeChannelId, replyingTo } = get()
    if (!activeChannelId || !serverId) return
    await sendMessage(serverId, activeChannelId, content, attachmentIds, replyingTo?.id ?? null)
    set({ replyingTo: null })
  },

  appendMessage: (msg) => {
    set((s) => {
      if (s.messages.find((m) => m.id === msg.id)) return s
      return { messages: [...s.messages, msg] }
    })
  },

  // Only append if the message belongs to the currently-viewed channel
  appendMessageForChannel: (channelId, msg) => {
    set((s) => {
      if (s.activeChannelId !== channelId) return s
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

  incrementUnread: (channelId) => {
    set((s) => ({
      unreadCounts: {
        ...s.unreadCounts,
        [channelId]: (s.unreadCounts[channelId] ?? 0) + 1,
      },
    }))
  },

  /* ── Pending attachments ──────────────────────────────────────── */
  addPendingAttachment: (file) => {
    const tempId = _nextTempId++
    set((s) => ({
      pendingAttachments: [
        ...s.pendingAttachments,
        { tempId, file, progress: 0, id: null, url: null, error: null },
      ],
    }))
    return tempId
  },

  updateAttachmentProgress: (tempId, progress) => {
    set((s) => ({
      pendingAttachments: s.pendingAttachments.map((a) =>
        a.tempId === tempId ? { ...a, progress } : a
      ),
    }))
  },

  finalizeAttachment: (tempId, data) => {
    set((s) => ({
      pendingAttachments: s.pendingAttachments.map((a) =>
        a.tempId === tempId ? { ...a, progress: 100, id: data.id, url: data.url } : a
      ),
    }))
  },

  setAttachmentError: (tempId, error) => {
    set((s) => ({
      pendingAttachments: s.pendingAttachments.map((a) =>
        a.tempId === tempId ? { ...a, error } : a
      ),
    }))
  },

  removePendingAttachment: (tempId) => {
    set((s) => ({
      pendingAttachments: s.pendingAttachments.filter((a) => a.tempId !== tempId),
    }))
  },

  clearPendingAttachments: () => set({ pendingAttachments: [] }),

  /* ── Voice counts ─────────────────────────────────────────────── */
  setChannelVoiceCount: (channelId, count) =>
    set((s) => ({
      channels: s.channels.map((c) =>
        c.id === channelId ? { ...c, voice_count: Math.max(0, count) } : c
      ),
    })),

  adjustChannelVoiceCount: (channelId, delta) =>
    set((s) => ({
      channels: s.channels.map((c) =>
        c.id === channelId
          ? { ...c, voice_count: Math.max(0, (c.voice_count ?? 0) + delta) }
          : c
      ),
    })),

  /* ── Reply ────────────────────────────────────────────────────── */
  setReplyingTo: (message) => set({ replyingTo: message }),
  clearReplyingTo: () => set({ replyingTo: null }),

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

  /* ── Voice ────────────────────────────────────────────────────── */
  voiceUsers: {},
  pendingVoiceSignals: [],

  setVoiceSnapshot: (users) => {
    const voiceUsers = {}
    users.forEach((u) => { voiceUsers[u.user_id] = { ...u } })
    set({ voiceUsers })
  },

  setVoiceUser: (userId, data) =>
    set((s) => ({
      voiceUsers: { ...s.voiceUsers, [userId]: { ...s.voiceUsers[userId], ...data } },
    })),

  removeVoiceUser: (userId) =>
    set((s) => {
      const next = { ...s.voiceUsers }
      delete next[userId]
      return { voiceUsers: next }
    }),

  pushVoiceSignal: (signal) =>
    set((s) => ({ pendingVoiceSignals: [...s.pendingVoiceSignals, signal] })),

  consumeVoiceSignals: () => {
    const signals = get().pendingVoiceSignals
    set({ pendingVoiceSignals: [] })
    return signals
  },
}))

export default useChatStore
