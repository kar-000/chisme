import { create } from 'zustand'
import { listDMs, getOrCreateDM, getDMMessages, sendDMMessage } from '../services/directMessages'

const useDMStore = create((set, get) => ({
  dms: [],               // list of DM channels
  activeDmId: null,
  dmMessages: [],        // messages for active DM
  dmMessagesTotal: 0,
  loadingDMMessages: false,

  /* ── DM Channels ──────────────────────────────────────────────── */
  fetchDMs: async () => {
    const { data } = await listDMs()
    set({ dms: data })
  },

  openDM: async (otherUserId) => {
    const { data } = await getOrCreateDM(otherUserId)
    set((s) => {
      const exists = s.dms.find((d) => d.id === data.id)
      return {
        dms: exists ? s.dms : [data, ...s.dms],
        activeDmId: data.id,
        dmMessages: [],
        dmMessagesTotal: 0,
      }
    })
    get().fetchDMMessages(data.id)
    return data
  },

  selectDM: (dmId) => {
    set({ activeDmId: dmId, dmMessages: [], dmMessagesTotal: 0 })
    get().fetchDMMessages(dmId)
  },

  closeDM: () => set({ activeDmId: null, dmMessages: [], dmMessagesTotal: 0 }),

  /* ── DM Messages ──────────────────────────────────────────────── */
  fetchDMMessages: async (dmId) => {
    set({ loadingDMMessages: true })
    try {
      const { data } = await getDMMessages(dmId, { limit: 50 })
      set({
        dmMessages: [...data.messages].reverse(),
        dmMessagesTotal: data.total,
        loadingDMMessages: false,
      })
    } catch {
      set({ loadingDMMessages: false })
    }
  },

  sendDMMessage: async (content, replyToId = null) => {
    const { activeDmId } = get()
    if (!activeDmId) return
    await sendDMMessage(activeDmId, content, replyToId)
    get().fetchDMMessages(activeDmId)
  },

  appendDMMessage: (msg) => {
    set((s) => {
      if (s.dmMessages.find((m) => m.id === msg.id)) return s
      // Also update last_message_at on the DM channel entry
      const dms = s.dms.map((d) =>
        d.id === msg.dm_channel_id ? { ...d, last_message_at: msg.created_at } : d
      )
      return { dmMessages: [...s.dmMessages, msg], dms }
    })
  },
}))

export default useDMStore
