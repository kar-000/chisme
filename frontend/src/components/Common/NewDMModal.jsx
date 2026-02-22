import { useEffect, useRef, useState } from 'react'
import { searchUsers } from '../../services/users'
import useDMStore from '../../store/dmStore'
import useChatStore from '../../store/chatStore'

/**
 * Overlay for starting a new DM.  Type to search users; click one to open a DM.
 * Close with Escape or clicking the backdrop.
 */
export default function NewDMModal({ onClose, onNavigate }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [opening, setOpening] = useState(false)
  const inputRef = useRef(null)
  const timerRef = useRef(null)

  const { openDM } = useDMStore()
  const clearActiveChannel = useChatStore((s) => s.clearActiveChannel)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const runSearch = async (q) => {
    if (!q.trim()) {
      setResults([])
      return
    }
    setLoading(true)
    try {
      const { data } = await searchUsers(q.trim())
      setResults(data)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const val = e.target.value
    setQuery(val)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => runSearch(val), 300)
  }

  const handleSelect = async (user) => {
    if (opening) return
    setOpening(true)
    try {
      clearActiveChannel()
      await openDM(user.id)
      onNavigate?.()
      onClose()
    } finally {
      setOpening(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Escape') onClose()
  }

  return (
    <div
      className="fixed inset-0 bg-black/80 z-50 flex items-start justify-center pt-[10vh] px-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-sm bg-[var(--bg-primary)] border-2 border-[var(--border-glow)]
                   rounded-lg shadow-glow-lg flex flex-col overflow-hidden"
        style={{ maxHeight: '60vh' }}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
          <span className="text-xs font-mono text-[var(--text-muted)] uppercase tracking-widest">
            New direct message
          </span>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Search input */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border)]">
          <span className="text-[var(--text-muted)] text-sm">@</span>
          <input
            ref={inputRef}
            value={query}
            onChange={handleChange}
            onKeyDown={handleKey}
            placeholder="Search by username…"
            className="flex-1 bg-transparent text-[var(--text-primary)] font-mono text-sm
                       placeholder:text-[var(--text-muted)] focus:outline-none"
          />
          {loading && (
            <span className="text-[var(--text-muted)] text-xs font-mono">…</span>
          )}
        </div>

        {/* Results */}
        <div className="overflow-y-auto flex-1">
          {results.length === 0 && query.trim() && !loading && (
            <p className="text-[var(--text-muted)] text-sm font-mono text-center py-6">
              No users found for &ldquo;{query}&rdquo;
            </p>
          )}
          {results.length === 0 && !query.trim() && (
            <p className="text-[var(--text-muted)] text-xs font-mono text-center py-6">
              Type a name to search
            </p>
          )}
          {results.map((u) => (
            <button
              key={u.id}
              onClick={() => handleSelect(u)}
              disabled={opening}
              className="w-full text-left px-4 py-3 border-b border-[var(--border)]
                         hover:bg-white/5 transition-colors flex items-center gap-3"
            >
              {u.avatar_url ? (
                <img
                  src={u.avatar_url}
                  alt=""
                  className="w-8 h-8 rounded object-cover flex-shrink-0"
                />
              ) : (
                <div className="w-8 h-8 rounded flex items-center justify-center text-xs font-bold
                                bg-gradient-to-br from-crt-teal to-crt-teal-lt text-crt-bg flex-shrink-0">
                  {u.username.slice(0, 2).toUpperCase()}
                </div>
              )}
              <div className="min-w-0">
                <p className="text-sm font-mono text-[var(--text-primary)] truncate">
                  {u.display_name || u.username}
                </p>
                {u.display_name && (
                  <p className="text-[10px] font-mono text-[var(--text-muted)] truncate">
                    @{u.username}
                  </p>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
