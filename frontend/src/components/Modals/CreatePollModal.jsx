import { useState, useEffect, useRef } from 'react'
import { createPoll } from '../../services/polls'
import useChatStore from '../../store/chatStore'
import useServerStore from '../../store/serverStore'

const DURATIONS = [
  { label: '1h', hours: 1 },
  { label: '6h', hours: 6 },
  { label: '24h', hours: 24 },
  { label: '72h', hours: 72 },
  { label: 'No expiry', hours: null },
]

export default function CreatePollModal({ onClose }) {
  const activeChannelId = useChatStore((s) => s.activeChannelId)
  const activeServerId = useServerStore((s) => s.activeServerId)
  const appendMessageForChannel = useChatStore((s) => s.appendMessageForChannel)

  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState(['', ''])
  const [multiChoice, setMultiChoice] = useState(false)
  const [durationHours, setDurationHours] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const setOption = (idx, val) =>
    setOptions((prev) => prev.map((o, i) => (i === idx ? val : o)))

  const addOption = () => {
    if (options.length < 6) setOptions((prev) => [...prev, ''])
  }

  const removeOption = (idx) => {
    if (options.length <= 2) return
    setOptions((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const q = question.trim()
    const opts = options.map((o) => o.trim()).filter(Boolean)
    if (!q) return setError('Question is required.')
    if (opts.length < 2) return setError('At least 2 non-empty options required.')

    setSubmitting(true)
    setError('')
    try {
      const { data } = await createPoll({
        channel_id: activeChannelId,
        server_id: activeServerId,
        question: q,
        options: opts,
        multi_choice: multiChoice,
        expires_in_hours: durationHours,
      })
      appendMessageForChannel(activeChannelId, data)
      onClose()
    } catch (err) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to create poll.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <form className="poll-modal" onSubmit={handleSubmit}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-mono text-[var(--text-secondary)] uppercase tracking-widest">
            Create Poll
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs"
          >
            ✕
          </button>
        </div>

        {/* Question */}
        <input
          ref={inputRef}
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          maxLength={300}
          className="w-full mb-3 bg-black/40 border border-[var(--border-primary)] rounded
                     text-[var(--text-primary)] font-mono text-sm px-3 py-2
                     focus:outline-none focus:border-[var(--accent-teal)] focus:shadow-[var(--glow-subtle)]"
        />

        {/* Options */}
        <div className="mb-1">
          {options.map((opt, i) => (
            <div key={i} className="poll-option-row">
              <input
                type="text"
                value={opt}
                onChange={(e) => setOption(i, e.target.value)}
                placeholder={`Option ${i + 1}`}
                maxLength={150}
              />
              {options.length > 2 && (
                <button
                  type="button"
                  className="poll-remove-btn"
                  onClick={() => removeOption(i)}
                  title="Remove option"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>

        {options.length < 6 && (
          <button
            type="button"
            onClick={addOption}
            className="text-xs font-mono text-[var(--accent-teal)] hover:underline mb-2"
          >
            + Add option
          </button>
        )}

        {/* Duration */}
        <div className="poll-duration-group">
          {DURATIONS.map((d) => (
            <button
              key={d.label}
              type="button"
              className={`poll-duration-btn${durationHours === d.hours ? ' active' : ''}`}
              onClick={() => setDurationHours(d.hours)}
            >
              {d.label}
            </button>
          ))}
        </div>

        {/* Multi-choice toggle */}
        <label className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)] cursor-pointer mb-3">
          <input
            type="checkbox"
            checked={multiChoice}
            onChange={(e) => setMultiChoice(e.target.checked)}
            className="accent-[var(--accent-teal)]"
          />
          Allow multiple choices
        </label>

        {error && (
          <p className="text-xs font-mono text-[var(--text-error)] mb-2">&gt; {error}</p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-mono text-[var(--text-muted)] hover:text-[var(--text-primary)] px-3 py-1.5
                       border border-[var(--border-primary)] rounded"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="text-xs font-mono px-3 py-1.5 rounded
                       bg-[var(--accent-teal)] text-[var(--bg-primary)]
                       disabled:opacity-50 disabled:cursor-not-allowed
                       hover:brightness-110 transition-all"
          >
            {submitting ? 'Creating…' : 'Create Poll'}
          </button>
        </div>
      </form>
    </div>
  )
}
