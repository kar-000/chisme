import { useState, useEffect, useRef } from 'react'
import useReminderStore from '../../store/reminderStore'

function tomorrowAt9am() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(9, 0, 0, 0)
  return d
}

const QUICK_OPTIONS = [
  { label: '15 min',       ms: 15 * 60 * 1000 },
  { label: '1 hour',       ms: 60 * 60 * 1000 },
  { label: '3 hours',      ms: 3 * 60 * 60 * 1000 },
  { label: 'Tomorrow 9am', ms: null, special: 'tomorrow-morning' },
]

export default function ReminderPicker({ messageId, onClose }) {
  const { addReminder } = useReminderStore()
  const [customTime, setCustomTime] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const ref = useRef(null)

  // Minimum value for the datetime-local input (now, formatted for the input)
  const minDt = new Date(Date.now() + 60_000).toISOString().slice(0, 16)

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('touchstart', handler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('touchstart', handler)
    }
  }, [onClose])

  const schedule = async (date) => {
    setSaving(true)
    setError('')
    try {
      await addReminder(messageId, date.toISOString())
      onClose()
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Could not set reminder')
      setSaving(false)
    }
  }

  const handleQuick = (opt) => {
    if (opt.special === 'tomorrow-morning') {
      schedule(tomorrowAt9am())
    } else {
      schedule(new Date(Date.now() + opt.ms))
    }
  }

  const handleCustom = () => {
    if (!customTime) return
    schedule(new Date(customTime))
  }

  return (
    <div
      ref={ref}
      className="
        absolute bottom-full right-0 mb-1 z-30
        bg-[var(--bg-secondary)] border border-[var(--border-glow)]
        rounded shadow-[0_4px_20px_rgba(0,0,0,0.5)]
        w-52 p-3
      "
      data-testid="reminder-picker"
    >
      <div className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mb-2">
        Remind me in…
      </div>

      <div className="flex flex-col gap-1.5 mb-3">
        {QUICK_OPTIONS.map((opt) => (
          <button
            key={opt.label}
            onClick={() => handleQuick(opt)}
            disabled={saving}
            className="
              w-full text-left font-mono text-sm px-2.5 py-1.5 rounded
              border border-[var(--border)] text-[var(--text-muted)]
              hover:border-[var(--accent-teal)] hover:text-[var(--accent-teal)]
              hover:bg-[var(--accent-teal)]/5
              disabled:opacity-40 transition-all
            "
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest">
          Custom
        </span>
        <input
          type="datetime-local"
          value={customTime}
          min={minDt}
          onChange={(e) => setCustomTime(e.target.value)}
          className="
            w-full bg-black/40 border border-[var(--border)] rounded px-2 py-1
            text-xs font-mono text-[var(--text-primary)]
            focus:outline-none focus:border-[var(--border-glow)]
          "
        />
        <button
          onClick={handleCustom}
          disabled={!customTime || saving}
          className="
            self-end font-mono text-xs px-2.5 py-1 rounded
            bg-[var(--accent-teal)]/10 border border-[var(--accent-teal)]
            text-[var(--accent-teal)]
            hover:bg-[var(--accent-teal)]/20
            disabled:opacity-40 transition-all
          "
        >
          Set
        </button>
      </div>

      {error && (
        <div className="mt-2 text-[10px] font-mono text-[var(--text-error)]">{error}</div>
      )}
    </div>
  )
}
