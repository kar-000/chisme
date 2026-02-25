import { useState } from 'react'
import SidePanel from './SidePanel'
import BookmarksPanel from './BookmarksPanel'
import RemindersPanel from './RemindersPanel'

export default function PersonalPanel({ onClose, onGoToMessage }) {
  const [tab, setTab] = useState('bookmarks')

  return (
    <SidePanel title={tab === 'bookmarks' ? 'Bookmarks' : 'Reminders'} onClose={onClose}>
      {/* Tab bar */}
      <div className="flex border-b border-[var(--border)] -mt-2 mb-3">
        <button
          onClick={() => setTab('bookmarks')}
          className={`
            flex-1 py-2 font-mono text-xs transition-all border-b-2
            ${tab === 'bookmarks'
              ? 'text-[var(--accent-teal)] border-[var(--accent-teal)]'
              : 'text-[var(--text-muted)] border-transparent hover:text-[var(--text-primary)]'}
          `}
        >
          🔖 Bookmarks
        </button>
        <button
          onClick={() => setTab('reminders')}
          className={`
            flex-1 py-2 font-mono text-xs transition-all border-b-2
            ${tab === 'reminders'
              ? 'text-[var(--accent-teal)] border-[var(--accent-teal)]'
              : 'text-[var(--text-muted)] border-transparent hover:text-[var(--text-primary)]'}
          `}
        >
          ⏰ Reminders
        </button>
      </div>

      {tab === 'bookmarks' ? (
        <BookmarksPanel embedded onClose={onClose} onGoToMessage={onGoToMessage} />
      ) : (
        <RemindersPanel onGoToMessage={onClose} />
      )}
    </SidePanel>
  )
}
