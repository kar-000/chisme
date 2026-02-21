import { useState, useRef, useEffect } from 'react'
import useDMStore from '../../store/dmStore'
import useAuthStore from '../../store/authStore'
import { useWebSocketDM } from '../../hooks/useWebSocketDM'
import Message from './Message'

function DMInput({ dmId }) {
  const [content, setContent] = useState('')
  const textareaRef = useRef(null)
  const { sendDMMessage } = useDMStore()

  const canSubmit = content.trim().length > 0

  const submit = async () => {
    if (!canSubmit) return
    const text = content.trim()
    setContent('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    try {
      await sendDMMessage(text)
    } catch (err) {
      console.error('DM send failed', err)
    }
  }

  const handleChange = (e) => {
    setContent(e.target.value)
    const el = textareaRef.current
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-[var(--border)] bg-black/20 flex-shrink-0 px-4 py-3 flex gap-2 items-end">
      <textarea
        ref={textareaRef}
        value={content}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Message…  (Enter to send, Shift+Enter for newline)"
        rows={1}
        className="
          flex-1 bg-black/40 border border-[var(--border)] rounded
          text-[var(--text-primary)] font-mono text-sm px-3 py-2
          placeholder:text-[var(--text-muted)]
          focus:outline-none focus:border-[var(--border-glow)]
          focus:shadow-[0_0_12px_rgba(0,206,209,0.3)]
          resize-none transition-all duration-200 leading-relaxed
        "
        data-testid="dm-input"
      />
      <button
        onClick={submit}
        disabled={!canSubmit}
        className="
          h-9 w-9 flex items-center justify-center rounded
          bg-gradient-to-br from-crt-teal to-crt-teal-lt
          text-crt-bg shadow-glow-sm
          hover:shadow-glow hover:-translate-y-px
          disabled:opacity-30 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0
          transition-all duration-200 flex-shrink-0
        "
        title="Send (Enter)"
        data-testid="dm-send-button"
      >
        ➤
      </button>
    </div>
  )
}

export default function DMView({ onBack }) {
  const { dmMessages, loadingDMMessages, activeDmId, dms } = useDMStore()
  const { token } = useAuthStore()
  const bottomRef = useRef(null)

  useWebSocketDM(activeDmId, token)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [dmMessages])

  const dm = dms.find((d) => d.id === activeDmId)
  const otherUsername = dm?.other_user?.username ?? '…'

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0" data-testid="dm-view">
      {/* DM header */}
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-2 flex-shrink-0">
        <button
          onClick={onBack}
          className="md:hidden text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg transition-colors flex-shrink-0"
          title="Back"
        >
          ←
        </button>
        <span className="text-[var(--text-muted)] font-mono text-sm">@</span>
        <h2 className="font-mono font-semibold text-[var(--text-primary)] tracking-wide">
          {otherUsername}
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-0.5 min-h-0">
        {loadingDMMessages && (
          <p className="text-center text-xs text-[var(--text-muted)] py-4">Loading…</p>
        )}
        {!loadingDMMessages && dmMessages.length === 0 && (
          <p className="text-center text-xs text-[var(--text-muted)] py-8">
            No messages yet. Say something!
          </p>
        )}
        {dmMessages.map((m) => (
          <Message key={m.id} message={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      <DMInput dmId={activeDmId} />
    </div>
  )
}
