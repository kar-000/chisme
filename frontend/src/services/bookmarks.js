import api from './api'

export const listBookmarks = () => api.get('/bookmarks')
export const createBookmark = (messageId, note = null) =>
  api.post('/bookmarks', { message_id: messageId, note })
export const updateBookmark = (bookmarkId, note) =>
  api.patch(`/bookmarks/${bookmarkId}`, { note })
export const deleteBookmark = (bookmarkId) => api.delete(`/bookmarks/${bookmarkId}`)
export const getBookmarkForMessage = (messageId) =>
  api.get(`/bookmarks/by-message/${messageId}`)
