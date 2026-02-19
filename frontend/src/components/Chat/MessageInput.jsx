import { useState, useRef, useCallback } from 'react'
import useChatStore from '../../store/chatStore'
import { uploadFile } from '../../services/uploads'
import AttachmentPreview from './AttachmentPreview'

const TYPING_THROTTLE = 2000

const ACCEPTED = 'image/*,video/mp4,video/webm,application/pdf,application/zip,text/plain'

export default function MessageInput({ onTyping }) {
  const [content, setContent] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const {
    sendMessage,
    activeChannelId,
    fetchMessages,
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

  const handleChange = (e) => {
    setContent(e.target.value)
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

  const uploadFiles = useCallback(async (files) => {
    for (const file of files) {
      const tempId = addPendingAttachment(file)
      try {
        const data = await uploadFile(file, (pct) =>
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
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    try {
      await sendMessage(text, readyIds)
      fetchMessages(activeChannelId)
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

      <div className="px-4 py-3 flex gap-2 items-end">
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
