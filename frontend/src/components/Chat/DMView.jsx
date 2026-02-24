import { useState, useRef, useEffect, useCallback } from 'react'
import useDMStore from '../../store/dmStore'
import useAuthStore from '../../store/authStore'
import { useWebSocketDM } from '../../hooks/useWebSocketDM'
import { attachGif } from '../../services/gifs'
import Message from './Message'
import GifPicker from './GifPicker'
import EmojiPicker from './EmojiPicker'

function DMInput({ dmId }) {
  const [content, setContent] = useState('')
  const [gifAttachmentId, setGifAttachmentId] = useState(null)
  const [showGifPicker, setShowGifPicker] = useState(false)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const textareaRef = useRef(null)
  const emojiButtonRef = useRef(null)
  const selectionRef = useRef({ start: 0, end: 0 })
  const { sendDMMessage } = useDMStore()

  const canSubmit = content.trim().length > 0 || gifAttachmentId != null

  const submit = async () => {
    if (!canSubmit) return
    const text = content.trim() || null
    const attachmentIds = gifAttachmentId ? [gifAttachmentId] : []
    setContent('')
    setGifAttachmentId(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    try {
      await sendDMMessage(text, attachmentIds)
    } catch (err) {
      console.error('DM send failed', err)
    }
  }

  const saveSelection = useCallback(() => {
    const el = textareaRef.current
    if (el) selectionRef.current = { start: el.selectionStart, end: el.selectionEnd }
  }, [])

  const insertEmoji = useCallback((emoji) => {
    saveSelection()
    const { start, end } = selectionRef.current
    setContent((prev) => prev.slice(0, start) + emoji + prev.slice(end))
    const nextPos = start + [...emoji].length
    selectionRef.current = { start: nextPos, end: nextPos }
    requestAnimationFrame(() => {
      const el = textareaRef.current
      if (el) {
        el.focus()
        el.selectionStart = nextPos
        el.selectionEnd = nextPos
      }
    })
  }, [saveSelection])

  const handleGifSelect = useCallback(async (gif) => {
    setShowGifPicker(false)
    try {
      const { data } = await attachGif(gif)
      setGifAttachmentId(data.id)
    } catch {
      // ignore — gif attach failure is non-fatal
    }
  }, [])

  const handleChange = (e) => {
    setContent(e.target.value)
    const el = textareaRef.current
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    saveSelection()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-[var(--border)] bg-black/20 flex-shrink-0">
      {/* GIF attached indicator */}
      {gifAttachmentId && (
        <div className="px-4 pt-2 flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
          <span>GIF attached</span>
          <button
            onClick={() => setGifAttachmentId(null)}
            className="text-[var(--text-muted)] hover:text-[var(--text-error)] transition-colors"
          >
            ✕
          </button>
        </div>
      )}

      <div className="px-4 py-3 flex gap-2 items-end relative">
        {/* GIF picker (positioned above) */}
        {showGifPicker && (
          <GifPicker
            onSelect={handleGifSelect}
            onClose={() => setShowGifPicker(false)}
          />
        )}

        {/* Emoji picker (positioned above) */}
        {showEmojiPicker && (
          <EmojiPicker
            onSelect={insertEmoji}
            onClose={() => setShowEmojiPicker(false)}
            anchorRef={emojiButtonRef}
          />
        )}

        {/* GIF button */}
        <button
          onClick={() => setShowGifPicker((v) => !v)}
          className="
            h-9 px-2 flex items-center justify-center rounded flex-shrink-0
            border border-[var(--border)] text-[var(--text-muted)]
            hover:text-[var(--accent-teal)] hover:border-[var(--border-glow)]
            hover:shadow-[0_0_8px_rgba(0,206,209,0.2)]
            transition-all duration-200 font-mono text-xs font-bold
          "
          title="Insert GIF"
          data-testid="dm-gif-button"
        >
          GIF
        </button>

        {/* Emoji button */}
        <button
          ref={emojiButtonRef}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => setShowEmojiPicker((v) => !v)}
          className="
            h-9 w-9 flex items-center justify-center rounded flex-shrink-0
            border border-[var(--border)] text-[var(--text-muted)]
            hover:text-[var(--accent-teal)] hover:border-[var(--border-glow)]
            hover:shadow-[0_0_8px_rgba(0,206,209,0.2)]
            transition-all duration-200 text-base
          "
          title="Insert emoji"
          data-testid="dm-emoji-button"
        >
          😊
        </button>

        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onSelect={saveSelection}
          onBlur={saveSelection}
          placeholder="Message…  (Enter to send, Shift+Enter for newline)"
          rows={1}
          className="
            flex-1 bg-black/40 border border-[var(--border)] rounded
            text-[var(--text-primary)] font-mono text-sm px-3 py-2
            placeholder:text-[var(--text-muted)]
            focus:outline-none focus:border-[var(--border-glow)]
            focus:shadow-[0_0_12px_rgba(0,206,209,0.3)]
            resize-none overflow-y-hidden transition-colors duration-200 leading-relaxed
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
      <div className="sticky top-0 z-10 px-4 py-3 border-b border-[var(--border)] bg-[var(--bg-primary)] flex items-center gap-2 flex-shrink-0">
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
