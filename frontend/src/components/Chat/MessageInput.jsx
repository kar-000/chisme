import { useState, useRef, useCallback } from 'react'
import useChatStore from '../../store/chatStore'
import { uploadFile } from '../../services/uploads'
import { attachGif } from '../../services/gifs'
import { getChannelMembers } from '../../services/channels'
import AttachmentPreview from './AttachmentPreview'
import GifPicker from './GifPicker'

const TYPING_THROTTLE = 2000

const ACCEPTED = 'image/*,video/mp4,video/webm,application/pdf,application/zip,text/plain'

/** Find an active @mention trigger at the cursor — returns { query, triggerStart } or null. */
function detectMention(text, cursorPos) {
  const before = text.slice(0, cursorPos)
  const atIdx = before.lastIndexOf('@')
  if (atIdx === -1) return null
  const fragment = before.slice(atIdx + 1)
  if (/\s/.test(fragment)) return null // space ends the mention token
  return { query: fragment, triggerStart: atIdx }
}

export default function MessageInput({ onTyping }) {
  const [content, setContent] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [showGifPicker, setShowGifPicker] = useState(false)

  // Mention autocomplete state
  const [mention, setMention] = useState(null) // { query, triggerStart } | null
  const [mentionUsers, setMentionUsers] = useState([])
  const [mentionIdx, setMentionIdx] = useState(0)
  const mentionTimerRef = useRef(null)

  const {
    sendMessage,
    activeChannelId,
    pendingAttachments,
    addPendingAttachment,
    updateAttachmentProgress,
    finalizeAttachment,
    setAttachmentError,
    removePendingAttachment,
    clearPendingAttachments,
    replyingTo,
    clearReplyingTo,
  } = useChatStore()
  const lastTypingSent = useRef(0)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleTyping = useCallback(() => {
    const now = Date.now()
    if (now - lastTypingSent.current > TYPING_THROTTLE) {
      lastTypingSent.current = now
      onTyping?.()
    }
  }, [onTyping])

  const closeMention = useCallback(() => {
    setMention(null)
    setMentionUsers([])
    setMentionIdx(0)
    clearTimeout(mentionTimerRef.current)
  }, [])

  const insertMention = useCallback((user) => {
    if (!user || !mention) return
    const cursor = textareaRef.current?.selectionStart ?? content.length
    const before = content.slice(0, mention.triggerStart)
    const after = content.slice(cursor)
    const inserted = `${before}@${user.username} ${after}`
    setContent(inserted)
    closeMention()
    // Restore focus and place cursor after the inserted mention
    const newCursor = before.length + user.username.length + 2 // '@' + name + ' '
    setTimeout(() => {
      textareaRef.current?.focus()
      textareaRef.current?.setSelectionRange(newCursor, newCursor)
    }, 0)
  }, [content, mention, closeMention])

  const handleChange = (e) => {
    const val = e.target.value
    setContent(val)

    // Auto-resize
    const el = textareaRef.current
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'

    handleTyping()

    // Mention detection
    const m = detectMention(val, e.target.selectionStart)
    if (m) {
      setMention(m)
      setMentionIdx(0)
      clearTimeout(mentionTimerRef.current)
      mentionTimerRef.current = setTimeout(async () => {
        if (!activeChannelId) return
        try {
          const { data } = await getChannelMembers(activeChannelId, m.query || undefined)
          const members = data.slice(0, 6)
          // Prepend @all if the typed prefix is compatible (empty, or starts with 'all')
          const q = m.query.toLowerCase()
          const showAll = 'all'.startsWith(q)
          const allEntry = { id: '__all__', username: 'all', display_name: 'Mention everyone' }
          setMentionUsers(showAll ? [allEntry, ...members] : members)
        } catch {
          setMentionUsers([])
        }
      }, 150)
    } else {
      closeMention()
    }
  }

  const handleKeyDown = (e) => {
    // Intercept arrow/enter/tab/escape when mention popup is open
    if (mention && mentionUsers.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setMentionIdx((i) => Math.min(i + 1, mentionUsers.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setMentionIdx((i) => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Tab' || e.key === 'Enter') {
        e.preventDefault()
        insertMention(mentionUsers[mentionIdx])
        return
      }
      if (e.key === 'Escape') {
        closeMention()
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const uploadFiles = useCallback(async (files) => {
    for (const file of files) {
      const tempId = addPendingAttachment(file)
      try {
        const { data } = await uploadFile(file, (pct) =>
          updateAttachmentProgress(tempId, pct),
        )
        finalizeAttachment(tempId, data)
      } catch (err) {
        const msg = err?.response?.data?.detail ?? 'Upload failed'
        setAttachmentError(tempId, msg)
      }
    }
  }, [addPendingAttachment, updateAttachmentProgress, finalizeAttachment, setAttachmentError])

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length) uploadFiles(files)
    e.target.value = ''
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length) uploadFiles(files)
  }, [uploadFiles])

  const handleGifSelect = useCallback(async (gif) => {
    const tempId = addPendingAttachment(null)
    try {
      const { data } = await attachGif(gif)
      finalizeAttachment(tempId, data)
    } catch {
      setAttachmentError(tempId, 'GIF attach failed')
    }
  }, [addPendingAttachment, finalizeAttachment, setAttachmentError])

  const isUploading = pendingAttachments.some((a) => a.progress < 100 && !a.error)
  const readyIds = pendingAttachments
    .filter((a) => a.progress === 100 && !a.error && a.id)
    .map((a) => a.id)
  const canSubmit = !isUploading && (content.trim().length > 0 || readyIds.length > 0)

  const submit = async () => {
    if (!canSubmit || !activeChannelId) return
    const text = content.trim()
    setContent('')
    clearPendingAttachments()
    closeMention()
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    try {
      await sendMessage(text, readyIds)
    } catch (err) {
      console.error('Send failed', err)
    }
  }

  return (
    <div
      className={`border-t border-[var(--border)] bg-black/20 flex-shrink-0 transition-colors duration-150 ${dragOver ? 'bg-[var(--accent-teal)]/10' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Reply preview strip */}
      {replyingTo && (
        <div
          className="flex items-center gap-2 px-4 pt-2 text-xs font-mono text-[var(--text-muted)]"
          data-testid="reply-preview"
        >
          <span className="text-[var(--accent-teal)]">↩ Replying to</span>
          <span className="text-[var(--text-lt)]">{replyingTo.user?.username}</span>
          <span className="truncate max-w-[300px] opacity-70">{replyingTo.content}</span>
          <button
            onClick={clearReplyingTo}
            className="ml-auto text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            title="Cancel reply"
            data-testid="cancel-reply"
          >
            ✕
          </button>
        </div>
      )}

      {pendingAttachments.length > 0 && (
        <AttachmentPreview
          attachments={pendingAttachments}
          onRemove={removePendingAttachment}
        />
      )}

      <div className="px-4 py-3 flex gap-2 items-end relative">
        {/* Mention autocomplete popup */}
        {mention && mentionUsers.length > 0 && (
          <div className="absolute bottom-full left-4 right-4 mb-1 bg-[var(--bg-primary)]
                          border border-[var(--border-glow)] rounded shadow-glow-lg overflow-hidden z-20">
            {mentionUsers.map((u, i) => (
              <button
                key={u.id}
                onMouseDown={(e) => { e.preventDefault(); insertMention(u) }}
                className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm font-mono
                            transition-colors border-b border-[var(--border)] last:border-0
                            ${i === mentionIdx
                              ? 'bg-white/10 text-[var(--text-primary)]'
                              : 'text-[var(--text-muted)] hover:bg-white/5'}`}
              >
                <span className={`flex-shrink-0 ${u.id === '__all__' ? 'text-[#FF8C42]' : 'text-[var(--accent-teal)]'}`}>@</span>
                <span className={u.id === '__all__' ? 'text-[#FF8C42] font-bold' : 'text-[var(--text-lt)]'}>{u.username}</span>
                {u.display_name && (
                  <span className="text-[var(--text-muted)] text-xs truncate">{u.display_name}</span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={handleFileChange}
          data-testid="file-input"
        />

        {/* GIF picker (positioned above this row) */}
        {showGifPicker && (
          <GifPicker
            onSelect={handleGifSelect}
            onClose={() => setShowGifPicker(false)}
          />
        )}

        {/* Paperclip button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="
            h-9 w-9 flex items-center justify-center rounded flex-shrink-0
            border border-[var(--border)] text-[var(--text-muted)]
            hover:text-[var(--text-primary)] hover:border-[var(--border-glow)]
            hover:shadow-[0_0_8px_rgba(0,206,209,0.2)]
            transition-all duration-200 text-base
          "
          title="Attach file"
          data-testid="attach-button"
        >
          📎
        </button>

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
          data-testid="gif-button"
        >
          GIF
        </button>

        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={dragOver ? 'Drop files here…' : 'Message…  (Enter to send, Shift+Enter for newline)'}
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
        >
          ➤
        </button>
      </div>
    </div>
  )
}
