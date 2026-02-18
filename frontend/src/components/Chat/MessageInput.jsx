import { useState, useRef, useCallback } from 'react'
import useChatStore from '../../store/chatStore'

const TYPING_THROTTLE = 2000

export default function MessageInput({ onTyping }) {
  const [content, setContent] = useState('')
  const { sendMessage, activeChannelId, fetchMessages } = useChatStore()
  const lastTypingSent = useRef(0)
  const textareaRef = useRef(null)

  const handleTyping = useCallback(() => {
    const now = Date.now()
    if (now - lastTypingSent.current > TYPING_THROTTLE) {
      lastTypingSent.current = now
      onTyping?.()
    }
  }, [onTyping])

  const handleChange = (e) => {
    setContent(e.target.value)
    // Auto-resize
    const el = textareaRef.current
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    handleTyping()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const submit = async () => {
    const text = content.trim()
    if (!text || !activeChannelId) return
    setContent('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    try {
      await sendMessage(text)
      // Refresh messages (WS will also push but REST is the fallback)
      fetchMessages(activeChannelId)
    } catch (err) {
      console.error('Send failed', err)
    }
  }

  return (
    <div className="px-4 py-3 border-t border-[var(--border)] bg-black/20 flex-shrink-0">
      <div className="flex gap-2 items-end">
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
            resize-none transition-all duration-200
            leading-relaxed
          "
        />
        <button
          onClick={submit}
          disabled={!content.trim()}
          className="
            h-9 w-9 flex items-center justify-center rounded
            bg-gradient-to-br from-crt-teal to-crt-teal-lt
            text-crt-bg shadow-glow-sm
            hover:shadow-glow hover:-translate-y-px
            disabled:opacity-30 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0
            transition-all duration-200 flex-shrink-0
          "
          title="Send (Enter)"
        >
          ➤
        </button>
      </div>
    </div>
  )
}
