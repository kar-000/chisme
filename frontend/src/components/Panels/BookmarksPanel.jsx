import { useEffect, useState } from 'react'
import SidePanel from './SidePanel'
import useBookmarkStore from '../../store/bookmarkStore'
import useChatStore from '../../store/chatStore'
import useServerStore from '../../store/serverStore'

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function BookmarkItem({ bookmark, onRemove, onGoTo, onEditNote }) {
  const [editingNote, setEditingNote] = useState(false)
  const [note, setNote] = useState(bookmark.note ?? '')
  const [saving, setSaving] = useState(false)

  const msg = bookmark.message
  const channelName = msg.channel_id ? `#${msg.channel?.name ?? msg.channel_id}` : 'DM'
  const author = msg.user?.username ?? 'unknown'
  const preview = msg.content?.slice(0, 120) || '(attachment)'

  const handleSaveNote = async () => {
    setSaving(true)
    await onEditNote(bookmark.id, note || null)
    setSaving(false)
    setEditingNote(false)
  }

  return (
    <div className="bookmark-item">
      <div className="bookmark-context">
        <span className="channel-ref">{channelName}</span>
        {' · '}
        <span>{author}</span>
        {' · '}
        <span>{formatDate(msg.created_at)}</span>
      </div>
      <div className="bookmark-preview" title={msg.content}>{preview}</div>
      {editingNote ? (
        <div className="flex flex-col gap-1 mb-2">
          <textarea
            className="bookmark-note-input"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={200}
            autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSaveNote() } }}
          />
          <div className="flex gap-1">
            <button
              type="button"
              disabled={saving}
              onClick={handleSaveNote}
              className="text-[10px] font-mono text-[var(--accent-teal)] hover:opacity-80 disabled:opacity-40"
            >
              {saving ? '…' : 'save'}
            </button>
            <button
              type="button"
              onClick={() => { setEditingNote(false); setNote(bookmark.note ?? '') }}
              className="text-[10px] font-mono text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              cancel
            </button>
          </div>
        </div>
      ) : bookmark.note ? (
        <div
          className="bookmark-note cursor-pointer hover:opacity-80"
          title="Click to edit note"
          onClick={() => setEditingNote(true)}
        >
          "{bookmark.note}"
        </div>
      ) : null}
      <div className="bookmark-actions">
        {msg.channel_id && (
          <button type="button" onClick={() => onGoTo(bookmark)}>go to</button>
        )}
        <button
          type="button"
          onClick={() => setEditingNote(true)}
          title="Edit note"
        >
          {bookmark.note ? 'edit note' : 'add note'}
        </button>
        <button
          type="button"
          onClick={() => onRemove(bookmark.id)}
          className="hover:border-[var(--text-error)] hover:text-[var(--text-error)]"
        >
          remove
        </button>
      </div>
    </div>
  )
}

export default function BookmarksPanel({ onClose, onGoToMessage }) {
  const { bookmarks, loading, fetchBookmarks, removeBookmark, editBookmarkNote } =
    useBookmarkStore()

  useEffect(() => {
    fetchBookmarks()
  }, [fetchBookmarks])

  return (
    <SidePanel title="Bookmarks" onClose={onClose}>
      {loading && (
        <p className="text-xs font-mono text-[var(--text-muted)] text-center py-6">Loading…</p>
      )}
      {!loading && bookmarks.length === 0 && (
        <p className="text-xs font-mono text-[var(--text-muted)] text-center py-6">
          No bookmarks yet. Hover a message and click 🔖 to save it.
        </p>
      )}
      {bookmarks.map((bm) => (
        <BookmarkItem
          key={bm.id}
          bookmark={bm}
          onRemove={removeBookmark}
          onGoTo={onGoToMessage}
          onEditNote={editBookmarkNote}
        />
      ))}
    </SidePanel>
  )
}
