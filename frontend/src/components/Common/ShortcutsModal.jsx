import Modal from './Modal'

const SHORTCUTS = [
  { keys: ['Ctrl', 'K'], description: 'Open message search' },
  { keys: ['Ctrl', '/'], description: 'Show this shortcuts panel' },
  { keys: ['Esc'], description: 'Close any open panel / modal' },
  { keys: ['↩'], description: 'Send message' },
  { keys: ['Shift', '↩'], description: 'New line in message' },
]

function Key({ label }) {
  return (
    <kbd
      className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded
                 border border-[var(--border-glow)] text-[var(--text-primary)]
                 bg-black/40 shadow-[0_1px_0_var(--border-glow)]"
    >
      {label}
    </kbd>
  )
}

export default function ShortcutsModal({ onClose }) {
  return (
    <Modal title="Keyboard Shortcuts" onClose={onClose}>
      <ul className="space-y-3">
        {SHORTCUTS.map(({ keys, description }) => (
          <li key={description} className="flex items-center justify-between gap-4">
            <span className="text-sm text-[var(--text-muted)] font-mono">{description}</span>
            <span className="flex items-center gap-1 flex-shrink-0">
              {keys.map((k, i) => (
                <span key={k} className="flex items-center gap-1">
                  {i > 0 && <span className="text-[var(--text-muted)] text-xs">+</span>}
                  <Key label={k} />
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>
    </Modal>
  )
}
