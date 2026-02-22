import { useState, useEffect, useRef, useCallback } from 'react'
import { searchGifs } from '../../services/gifs'

export default function GifPicker({ onSelect, onClose }) {
  const [query, setQuery] = useState('')
  const [gifs, setGifs] = useState([])
  const [loading, setLoading] = useState(true)
  const containerRef = useRef(null)
  const debounceRef = useRef(null)

  const fetchGifs = useCallback(async (q) => {
    setLoading(true)
    try {
      const { data } = await searchGifs(q)
      setGifs(data)
    } catch {
      setGifs([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Load featured GIFs on mount
  useEffect(() => {
    fetchGifs('')
  }, [fetchGifs])

  // Debounce search query changes
  const handleSearchChange = (e) => {
    const q = e.target.value
    setQuery(q)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchGifs(q), 300)
  }

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  // Escape key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      ref={containerRef}
      className="absolute bottom-full left-0 mb-2 w-80 max-w-[calc(100vw-2rem)] bg-[var(--bg-primary)] border border-[var(--border-glow)] rounded shadow-[0_0_16px_rgba(0,206,209,0.25)] z-20"
      data-testid="gif-picker"
    >
      {/* Search input */}
      <div className="p-2 border-b border-[var(--border)]">
        <input
          type="text"
          value={query}
          onChange={handleSearchChange}
          placeholder="Search GIFs…"
          autoFocus
          className="
            w-full bg-black/40 border border-[var(--border)] rounded px-2 py-1
            text-sm font-mono text-[var(--text-primary)] placeholder:text-[var(--text-muted)]
            focus:outline-none focus:border-[var(--border-glow)]
          "
          data-testid="gif-search-input"
        />
      </div>

      {/* GIF grid */}
      <div className="p-2 h-60 overflow-y-auto">
        {loading ? (
          <div
            className="flex items-center justify-center h-full text-[var(--text-muted)] font-mono text-xs"
            data-testid="gif-loading"
          >
            loading…
          </div>
        ) : gifs.length === 0 ? (
          <div
            className="flex items-center justify-center h-full text-[var(--text-muted)] font-mono text-xs"
            data-testid="gif-empty"
          >
            No results
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-1">
            {gifs.map((gif) => (
              <button
                key={gif.id}
                onClick={() => { onSelect(gif); onClose() }}
                className="
                  rounded overflow-hidden border border-transparent
                  hover:border-[var(--border-glow)] hover:shadow-[0_0_6px_rgba(0,206,209,0.3)]
                  transition-all cursor-pointer p-0
                "
                data-testid="gif-item"
              >
                <img
                  src={gif.preview_url}
                  alt={gif.title}
                  className="w-full h-16 object-cover"
                />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
