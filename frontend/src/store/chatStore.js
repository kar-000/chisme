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
  // progress 0-100, id/url set after upload completes
  pendingAttachments: [],

  // Quote-reply: the message being replied to (or null)
  replyingTo: null,

  // Unread counts: { [channelId]: number } — populated from API, cleared on select
  unreadCounts: {},

  /* ── Channels ─────────────────────────────────────────────────── */
  fetchChannels: async () => {
    const { data } = await listChannels({ limit: 100 })
    // Populate unread counts from the server response
    const unreadCounts = {}
    data.forEach((c) => { unreadCounts[c.id] = c.unread_count ?? 0 })
    set({ channels: data, unreadCounts })
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
    // Clear unread badge immediately (optimistic)
    set((s) => ({
      activeChannelId: channelId,
      messages: [],
      messagesTotal: 0,
      typingUsers: [],
      pendingAttachments: [],
      replyingTo: null,
      unreadCounts: { ...s.unreadCounts, [channelId]: 0 },
    }))
    get().fetchMessages(channelId)
    // Persist read position on the server (fire-and-forget)
    markChannelRead(channelId).catch(() => {})
  },

  clearActiveChannel: () => {
    set({ activeChannelId: null, messages: [], messagesTotal: 0, typingUsers: [], pendingAttachments: [], replyingTo: null })
  },

  /* ── Messages ─────────────────────────────────────────────────── */
  fetchMessages: async (channelId) => {
    set({ loadingMessages: true })
    try {
      const { data } = await getMessages(channelId, { limit: 50 })
      set({ messages: [...data.messages].reverse(), messagesTotal: data.total, loadingMessages: false })
    } catch {
      set({ loadingMessages: false })
    }
  },

  sendMessage: async (content, attachmentIds = []) => {
    const { activeChannelId, replyingTo } = get()
    if (!activeChannelId) return
    await sendMessage(activeChannelId, content, attachmentIds, replyingTo?.id ?? null)
    set({ replyingTo: null })
  },

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

  /* ── Pending attachments ──────────────────────────────────────── */
  addPendingAttachment: (file) => {
    const tempId = _nextTempId++
    set((s) => ({
      pendingAttachments: [...s.pendingAttachments, { tempId, file, progress: 0, id: null, url: null, error: null }],
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

  /* ── Voice counts (per-channel, for sidebar indicator) ───────── */
  // Absolute set — used when we receive a voice.state_snapshot
  setChannelVoiceCount: (channelId, count) =>
    set((s) => ({
      channels: s.channels.map((c) =>
        c.id === channelId ? { ...c, voice_count: Math.max(0, count) } : c
      ),
    })),

  // Delta update — used on voice.user_joined (+1) / voice.user_left (-1)
  adjustChannelVoiceCount: (channelId, delta) =>
    set((s) => ({
      channels: s.channels.map((c) =>
        c.id === channelId ? { ...c, voice_count: Math.max(0, (c.voice_count ?? 0) + delta) } : c
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
  // voiceUsers: { [user_id]: { user_id, username, muted, video } }
  voiceUsers: {},
  // pendingVoiceSignals: queue of { type, from_user_id, sdp?, candidate? }
  pendingVoiceSignals: [],

  setVoiceUser: (userId, data) =>
    set((s) => ({ voiceUsers: { ...s.voiceUsers, [userId]: { ...s.voiceUsers[userId], ...data } } })),

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
