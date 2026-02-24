import { useState, useEffect } from 'react'

function fmtTime(secs) {
  return `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`
}

export default function VoiceRecordingBar({ onStop, onCancel }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="px-4 py-3 flex items-center gap-3" data-testid="voice-recording-bar">
      {/* Pulsing red dot */}
      <span className="w-2.5 h-2.5 rounded-full bg-[var(--text-error)] animate-pulse flex-shrink-0" />

      <span className="font-mono text-sm text-[var(--text-error)] tabular-nums">
        {fmtTime(elapsed)}
      </span>

      <span className="font-mono text-xs text-[var(--text-muted)] flex-1 truncate">
        Recording…
      </span>

      {/* Stop & send */}
      <button
        onClick={onStop}
        className="
          h-8 px-3 flex items-center gap-1.5 rounded flex-shrink-0
          border border-[var(--border-glow)] text-[var(--accent-teal)]
          hover:bg-[var(--accent-teal)]/10 transition-all duration-150
          font-mono text-xs
        "
        title="Stop and send voice message"
        data-testid="voice-stop-button"
      >
        ■ Send
      </button>

      {/* Cancel */}
      <button
        onClick={onCancel}
        className="
          h-8 px-3 flex items-center rounded flex-shrink-0
          border border-[var(--border)] text-[var(--text-muted)]
          hover:text-[var(--text-primary)] hover:border-[var(--border-glow)]
          transition-all duration-150 font-mono text-xs
        "
        title="Cancel recording"
        data-testid="voice-cancel-button"
      >
        ✕
      </button>
    </div>
  )
}
