/**
 * Shared slide-in panel shell.
 * Used by Bookmarks, Reminders, and future feature panels.
 */
export default function SidePanel({ title, onClose, children }) {
  return (
    <div className="side-panel">
      <div className="side-panel-header">
        <span>{title}</span>
        <button
          type="button"
          onClick={onClose}
          className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors text-lg leading-none"
          title="Close panel"
        >
          ✕
        </button>
      </div>
      <div className="side-panel-body">
        {children}
      </div>
    </div>
  )
}
