import { useEffect, useRef, useState } from 'react'
import { searchMessages } from '../../services/search'
import useChatStore from '../../store/chatStore'
import useDMStore from '../../store/dmStore'

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
    ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/**
 * Full-screen search overlay.  Close with Escape or clicking the backdrop.
 */
export default function MessageSearch({ onClose }) {
  const [query, setQuery] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const inputRef = useRef(null)
  const timerRef = useRef(null)

  const channels = useChatStore((s) => s.channels)
  const { selectChannel } = useChatStore()
  const closeDM = useDMStore((s) => s.closeDM)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const runSearch = async (q, chId) => {
    if (!q.trim()) {
      setResults([])
      setSearched(false)
      return
    }
    setLoading(true)
    try {
      const res = await searchMessages(q.trim(), chId || undefined)
      setResults(res.data.results)
      setSearched(true)
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
    timerRef.current = setTimeout(() => runSearch(val, channelFilter), 400)
  }

  const handleChannelFilter = (e) => {
    const val = e.target.value
    setChannelFilter(val)
    if (query.trim()) runSearch(query, val)
  }

  const handleSelect = (result) => {
    closeDM()
    selectChannel(result.channel_id)
    onClose()
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
        className="w-full max-w-xl bg-[var(--bg-primary)] border-2 border-[var(--border-glow)]
                   rounded-lg shadow-glow-lg flex flex-col overflow-hidden"
        style={{ maxHeight: '70vh' }}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border)]">
          <span className="text-[var(--text-muted)] text-sm">🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={handleChange}
            onKeyDown={handleKey}
            placeholder="Search messages…"
            className="flex-1 bg-transparent text-[var(--text-primary)] font-mono text-sm
                       placeholder:text-[var(--text-muted)] focus:outline-none"
          />
          {loading && (
            <span className="text-[var(--text-muted)] text-xs font-mono">searching…</span>
          )}
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Channel filter */}
        <div className="px-4 py-2 border-b border-[var(--border)] flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase tracking-widest shrink-0">
            Channel
          </span>
          <select
            value={channelFilter}
            onChange={handleChannelFilter}
            className="flex-1 bg-black/40 border border-[var(--border)] rounded px-2 py-0.5
                       text-xs font-mono text-[var(--text-primary)] focus:outline-none
                       focus:border-[var(--border-glow)]"
          >
            <option value="">All channels</option>
            {channels.map((ch) => (
              <option key={ch.id} value={ch.id}>#{ch.name}</option>
            ))}
          </select>
        </div>

        {/* Results */}
        <div className="overflow-y-auto flex-1">
          {results.length === 0 && searched && !loading && (
            <p className="text-[var(--text-muted)] text-sm font-mono text-center py-6">
              No results for "{query}"
            </p>
          )}
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => handleSelect(r)}
              className="w-full text-left px-4 py-3 border-b border-[var(--border)]
                         hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-[var(--text-lt)] font-mono">
                  {r.user.display_name || r.user.username}
                </span>
                {r.channel_name && (
                  <span className="text-[10px] text-[var(--text-muted)] font-mono">
                    #{r.channel_name}
                  </span>
                )}
                <span className="text-[10px] text-[var(--text-muted)] font-mono ml-auto">
                  {formatDate(r.created_at)}
                </span>
              </div>
              <p className="text-sm text-[var(--text-primary)] font-mono truncate leading-snug">
                {r.content}
              </p>
            </button>
          ))}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2 border-t border-[var(--border)] flex gap-4">
          <span className="text-[10px] text-[var(--text-muted)] font-mono">↵ jump to channel</span>
          <span className="text-[10px] text-[var(--text-muted)] font-mono">Esc close</span>
        </div>
      </div>
    </div>
  )
}
