import useChatStore from '../../store/chatStore'
import useChannelNotesStore from '../../store/channelNotesStore'

export default function Header({ onBack, onBookmarksOpen, notesOpen, onNotesToggle }) {
  const { channels, activeChannelId } = useChatStore()
  const channel = channels.find((c) => c.id === activeChannelId)
  const notesCache = useChannelNotesStore((s) => s.cache)
  const hasNotes = Boolean(notesCache[activeChannelId]?.content?.trim())

  if (!channel) return null

  return (
    <header className="sticky top-0 z-10 px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-primary)] flex items-center gap-3 flex-shrink-0">
      <button
        onClick={onBack}
        className="md:hidden text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg transition-colors flex-shrink-0"
        title="Back to channels"
      >
        ←
      </button>
      <div className="flex-1 min-w-0">
        <h2 className="text-lg font-medium text-[var(--text-primary)] glow-teal">
          <span className="text-[var(--text-muted)]"># </span>{channel.name}
        </h2>
        {channel.description && (
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{channel.description}</p>
        )}
      </div>
      {onNotesToggle && (
        <button
          onClick={onNotesToggle}
          className={`relative transition-colors flex-shrink-0 text-lg ${notesOpen ? 'text-[var(--accent-teal)]' : 'text-[var(--text-muted)] hover:text-[var(--accent-teal)]'}`}
          title={notesOpen ? 'Hide channel notes' : 'Channel notes'}
        >
          📌
          {hasNotes && !notesOpen && (
            <span className="notes-active-dot" />
          )}
        </button>
      )}
      {onBookmarksOpen && (
        <button
          onClick={onBookmarksOpen}
          className="text-[var(--text-muted)] hover:text-[var(--accent-teal)] transition-colors flex-shrink-0 text-lg"
          title="Bookmarks"
        >
          🔖
        </button>
      )}
    </header>
  )
}
