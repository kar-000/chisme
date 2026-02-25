import { useEffect, useRef, useState } from 'react'
import { searchMessages } from '../../services/search'
import useChatStore from '../../store/chatStore'
import useDMStore from '../../store/dmStore'
import useServerStore from '../../store/serverStore'

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
    ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const EMPTY_FILTERS = { from_user: '', after: '', before: '', has_link: false, has_file: false }

function hasActiveFilters(f) {
  return !!(f.from_user || f.after || f.before || f.has_link || f.has_file)
}

function FilterChip({ label, onRemove }) {
  return (
    <span className="search-filter-chip">
      {label}
      <button type="button" onClick={onRemove}>✕</button>
    </span>
  )
}

/**
 * Full-screen search overlay.  Close with Escape or clicking the backdrop.
 */
export default function MessageSearch({ onClose }) {
  const [query, setQuery] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const inputRef = useRef(null)
  const timerRef = useRef(null)

  const channels = useChatStore((s) => s.channels)
  const { selectChannel } = useChatStore()
  const closeDM = useDMStore((s) => s.closeDM)
  const activeServerId = useServerStore((s) => s.activeServerId)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const runSearch = async (q, chId, f) => {
    if (!q.trim() && !hasActiveFilters(f) && !chId) {
      setResults([])
      setSearched(false)
      return
    }
    setLoading(true)
    try {
      const res = await searchMessages(q.trim(), chId || undefined, f)
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
    timerRef.current = setTimeout(() => runSearch(val, channelFilter, filters), 400)
  }

  const handleChannelFilter = (e) => {
    const val = e.target.value
    setChannelFilter(val)
    runSearch(query, val, filters)
  }

  const updateFilter = (patch) => {
    const next = { ...filters, ...patch }
    setFilters(next)
    runSearch(query, channelFilter, next)
  }

  const handleSelect = (result) => {
    closeDM()
    selectChannel(activeServerId, result.channel_id)
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
        {/* Query input */}
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
            type="button"
            onClick={() => setFiltersOpen((o) => !o)}
            title="Toggle filters"
            className={`text-xs font-mono px-2 py-0.5 rounded border transition-colors
              ${filtersOpen || hasActiveFilters(filters)
                ? 'border-[var(--accent-teal)] text-[var(--accent-teal)]'
                : 'border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--accent-teal)] hover:text-[var(--accent-teal)]'}`}
          >
            ⊞ filters
          </button>
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

        {/* Expanded filter row */}
        {filtersOpen && (
          <div className="px-4 py-2 border-b border-[var(--border)] flex flex-wrap gap-3 bg-black/20">
            <label className="flex flex-col gap-0.5">
              <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest">From</span>
              <input
                className="search-filter-input"
                placeholder="username"
                value={filters.from_user}
                onChange={(e) => updateFilter({ from_user: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-0.5">
              <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest">After</span>
              <input
                type="date"
                className="search-filter-input"
                value={filters.after}
                onChange={(e) => updateFilter({ after: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-0.5">
              <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest">Before</span>
              <input
                type="date"
                className="search-filter-input"
                value={filters.before}
                onChange={(e) => updateFilter({ before: e.target.value })}
              />
            </label>
            <div className="flex flex-col gap-1 justify-end">
              <label className="flex items-center gap-1.5 text-xs font-mono text-[var(--text-secondary)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.has_link}
                  onChange={(e) => updateFilter({ has_link: e.target.checked })}
                  className="accent-[var(--accent-teal)]"
                />
                Has link
              </label>
              <label className="flex items-center gap-1.5 text-xs font-mono text-[var(--text-secondary)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.has_file}
                  onChange={(e) => updateFilter({ has_file: e.target.checked })}
                  className="accent-[var(--accent-teal)]"
                />
                Has file
              </label>
            </div>
          </div>
        )}

        {/* Active filter chips */}
        {hasActiveFilters(filters) && (
          <div className="px-4 py-1.5 border-b border-[var(--border)] flex flex-wrap gap-1.5 bg-black/10">
            {filters.from_user && (
              <FilterChip label={`from: ${filters.from_user}`} onRemove={() => updateFilter({ from_user: '' })} />
            )}
            {filters.after && (
              <FilterChip label={`after: ${filters.after}`} onRemove={() => updateFilter({ after: '' })} />
            )}
            {filters.before && (
              <FilterChip label={`before: ${filters.before}`} onRemove={() => updateFilter({ before: '' })} />
            )}
            {filters.has_link && (
              <FilterChip label="has: link" onRemove={() => updateFilter({ has_link: false })} />
            )}
            {filters.has_file && (
              <FilterChip label="has: file" onRemove={() => updateFilter({ has_file: false })} />
            )}
          </div>
        )}

        {/* Results */}
        <div className="overflow-y-auto flex-1">
          {results.length === 0 && searched && !loading && (
            <p className="text-[var(--text-muted)] text-sm font-mono text-center py-6">
              No results found
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
