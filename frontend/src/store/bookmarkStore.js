import { create } from 'zustand'
import {
  listBookmarks,
  createBookmark,
  updateBookmark,
  deleteBookmark,
} from '../services/bookmarks'

const useBookmarkStore = create((set, get) => ({
  bookmarks: [],
  loading: false,
  // Set of bookmarked message IDs for O(1) lookup
  bookmarkedMessageIds: new Set(),

  fetchBookmarks: async () => {
    set({ loading: true })
    try {
      const { data } = await listBookmarks()
      set({
        bookmarks: data,
        bookmarkedMessageIds: new Set(data.map((b) => b.message_id)),
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },

  addBookmark: async (messageId, note = null) => {
    const { data } = await createBookmark(messageId, note)
    set((s) => ({
      bookmarks: [data, ...s.bookmarks],
      bookmarkedMessageIds: new Set([...s.bookmarkedMessageIds, messageId]),
    }))
    return data
  },

  editBookmarkNote: async (bookmarkId, note) => {
    const { data } = await updateBookmark(bookmarkId, note)
    set((s) => ({
      bookmarks: s.bookmarks.map((b) => (b.id === bookmarkId ? data : b)),
    }))
  },

  removeBookmark: async (bookmarkId) => {
    const bm = get().bookmarks.find((b) => b.id === bookmarkId)
    await deleteBookmark(bookmarkId)
    set((s) => {
      const bookmarks = s.bookmarks.filter((b) => b.id !== bookmarkId)
      const bookmarkedMessageIds = new Set(bookmarks.map((b) => b.message_id))
      return { bookmarks, bookmarkedMessageIds }
    })
    return bm?.message_id
  },

  removeBookmarkByMessageId: async (messageId) => {
    const bm = get().bookmarks.find((b) => b.message_id === messageId)
    if (!bm) return
    await deleteBookmark(bm.id)
    set((s) => {
      const bookmarks = s.bookmarks.filter((b) => b.id !== bm.id)
      const bookmarkedMessageIds = new Set(bookmarks.map((b) => b.message_id))
      return { bookmarks, bookmarkedMessageIds }
    })
  },
}))

export default useBookmarkStore
