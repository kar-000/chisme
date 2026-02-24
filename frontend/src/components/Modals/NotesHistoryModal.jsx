import { useState, useEffect } from 'react'
import useChannelNotesStore from '../../store/channelNotesStore'

function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function NotesHistoryModal({ channelId, onClose }) {
  const { fetchHistory } = useChannelNotesStore()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHistory(channelId).then((data) => {
      setHistory(data ?? [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [channelId, fetchHistory])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={onClose}
      data-testid="notes-history-modal"
    >
      <div
        className="bg-[var(--bg-secondary)] border border-[var(--border-glow)] rounded shadow-2xl
                   w-[560px] max-w-[calc(100vw-2rem)] max-h-[70vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
          <span className="font-mono text-sm text-[var(--text-primary)]">📌 Notes History</span>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg leading-none transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1">
          {loading && (
            <p className="text-xs font-mono text-[var(--text-muted)] text-center py-8">Loading…</p>
          )}
          {!loading && history.length === 0 && (
            <p className="text-xs font-mono text-[var(--text-muted)] text-center py-8">
              No revision history yet.
            </p>
          )}
          {history.map((entry) => (
            <div key={entry.id} className="history-entry">
              <div className="history-entry-meta">
                v{entry.version} · {entry.edited_by_username ?? 'unknown'} · {formatDate(entry.edited_at)}
              </div>
              <div className="history-entry-preview">
                {entry.content?.trim() || '(empty)'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
