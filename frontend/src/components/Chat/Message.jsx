import { useState, useRef } from 'react'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'
import ProfileModal from '../Common/ProfileModal'
import { getUserByUsername } from '../../services/users'
import EmojiPicker from './EmojiPicker'
import TwemojiEmoji from '../Common/TwemojiEmoji'

/**
 * Render message content with clickable, highlighted @mentions.
 * Mentions matching the current user get an orange highlight.
 */
function MessageContent({ content, currentUsername, isOwn, onMentionClick }) {
  const parts = content.split(/(@\w+)/g)
  return (
    <span>
      {parts.map((part, i) => {
        if (!part.startsWith('@')) return part
        const name = part.slice(1)
        const isAll = name.toLowerCase() === 'all'
        const isMe = !isAll && name.toLowerCase() === currentUsername?.toLowerCase()
        const highlight = isAll || isMe
        return (
          <button
            key={i}
            onClick={() => !isAll && onMentionClick(name)}
            className={`font-bold font-mono transition-colors
              ${highlight
                ? 'text-[var(--crt-orange,#FF8C42)] bg-[rgba(255,140,66,0.15)] px-0.5 rounded hover:bg-[rgba(255,140,66,0.25)]'
                : isOwn
                  ? 'text-[var(--text-own)] hover:underline'
                  : 'text-[var(--text-lt)] hover:underline'
              }`}
          >
            {part}
          </button>
        )
      })}
    </span>
  )
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function Attachments({ attachments }) {
  const [lightbox, setLightbox] = useState(null)

  if (!attachments?.length) return null

  return (
    <>
      <div className="flex flex-wrap gap-2 mt-1.5">
        {attachments.map((a) => {
          const isImage = a.mime_type.startsWith('image/')
          const isVideo = a.mime_type.startsWith('video/')

          if (isImage) {
            return (
              <img
                key={a.id}
                src={a.thumbnail_url || a.url}
                alt={a.original_filename}
                className="max-h-48 rounded border border-[var(--border)] object-cover cursor-pointer
                           hover:border-[var(--border-glow)] hover:shadow-glow-sm transition-all"
                onClick={() => setLightbox(a.url)}
                data-testid="attachment-image"
              />
            )
          }

          if (isVideo) {
            return (
              <video
                key={a.id}
                src={a.url}
                controls
                className="max-h-48 rounded border border-[var(--border)]"
                data-testid="attachment-video"
              />
            )
          }

          // Generic file card
          return (
            <a
              key={a.id}
              href={a.url}
              download={a.original_filename}
              className="flex items-center gap-2 px-3 py-2 rounded border border-[var(--border)]
                         bg-black/40 hover:border-[var(--border-glow)] hover:bg-black/60
                         transition-all duration-150 text-[var(--text-primary)] no-underline"
              data-testid="attachment-file"
            >
              <span className="text-lg">📎</span>
              <div className="min-w-0">
                <div className="text-xs font-mono truncate max-w-[160px]">{a.original_filename}</div>
                <div className="text-[10px] text-[var(--text-muted)] font-mono">{formatBytes(a.size)}</div>
              </div>
            </a>
          )
        })}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center cursor-pointer"
          onClick={() => setLightbox(null)}
          data-testid="lightbox"
        >
          <img
            src={lightbox}
            alt="Full size"
            className="max-h-[90vh] max-w-[90vw] rounded shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  )
}

function QuotedMessage({ reply }) {
  if (!reply) return null
  return (
    <div
      className="mb-1 pl-2 border-l-2 border-[var(--accent-teal)] text-[var(--text-muted)] text-xs font-mono truncate"
      data-testid="quoted-message"
    >
      <span className="text-[var(--text-lt)] mr-1">{reply.user?.username}</span>
      <span className="opacity-70">{reply.content}</span>
    </div>
  )
}

function formatTime(iso) {
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function ReactionBar({ reactions = [], messageId }) {
  const { addReaction, removeReaction } = useChatStore()
  const { user } = useAuthStore()

  const grouped = reactions.reduce((acc, r) => {
    if (!acc[r.emoji]) acc[r.emoji] = { count: 0, users: [] }
    acc[r.emoji].count++
    acc[r.emoji].users.push(r.user_id)
    return acc
  }, {})

  if (!Object.keys(grouped).length) return null

  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {Object.entries(grouped).map(([emoji, { count, users }]) => {
        const reacted = users.includes(user?.id)
        return (
          <button
            key={emoji}
            onClick={() =>
              reacted
                ? removeReaction(messageId, emoji, user.id)
                : addReaction(messageId, emoji)
            }
            className={`
              flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border transition-all
              ${reacted
                ? 'bg-[var(--bg-active)] border-[var(--accent-teal)] text-[var(--text-primary)]'
                : 'bg-[var(--bg-hover)] border-[var(--border)] text-[var(--text-lt)] hover:border-[var(--accent-teal)]'
              }
            `}
          >
            <TwemojiEmoji emoji={emoji} size="1em" />
            <span className="text-[var(--text-muted)] font-mono">{count}</span>
          </button>
        )
      })}
    </div>
  )
}

export default function Message({ message }) {
  const { user } = useAuthStore()
  const { editMessage, deleteMessage, addReaction, setReplyingTo } = useChatStore()
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.content)
  const [showActions, setShowActions] = useState(false)
  const [showReactionPicker, setShowReactionPicker] = useState(false)
  const [profileUserId, setProfileUserId] = useState(null)
  const reactionButtonRef = useRef(null)

  const isOwn = message.user_id === user?.id

  const handleEdit = async (e) => {
    e.preventDefault()
    if (!editContent.trim()) return
    await editMessage(message.id, editContent)
    setEditing(false)
  }

  const handleDelete = () => {
    if (confirm('Delete this message?')) deleteMessage(message.id)
  }

  const quickReact = (emoji) => addReaction(message.id, emoji)

  return (
    <>
    <div
      className={`
        group flex gap-3 px-3 py-2 rounded transition-all duration-150 msg-appear
        ${isOwn ? 'bg-[rgba(255,182,193,0.06)]' : 'hover:bg-[rgba(0,206,209,0.04)]'}
      `}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      {message.user?.avatar_url ? (
        <img
          src={message.user.avatar_url}
          alt={message.user.username}
          className="w-8 h-8 rounded flex-shrink-0 object-cover border border-[var(--border)] mt-0.5"
        />
      ) : (
        <div
          className="w-8 h-8 rounded flex-shrink-0 flex items-center justify-center
                     text-[10px] font-bold bg-gradient-to-br from-crt-teal to-crt-teal-lt
                     text-crt-bg shadow-glow-sm mt-0.5"
        >
          {message.user?.username?.slice(0, 2).toUpperCase()}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-0.5">
          <button
            onClick={() => setProfileUserId(message.user_id)}
            className="text-sm font-medium text-[var(--text-lt)] hover:underline cursor-pointer bg-transparent border-none p-0"
            style={{ textShadow: '0 0 4px rgba(93,173,226,0.4)' }}
          >
            {message.user?.username}
          </button>
          <span className="text-[10px] text-[var(--text-muted)]">
            {formatTime(message.created_at)}
          </span>
          {message.edited_at && (
            <span className="text-[10px] text-[var(--text-muted)] italic">(edited)</span>
          )}
        </div>

        {/* Quoted message */}
        <QuotedMessage reply={message.reply_to} />

        {editing ? (
          <form onSubmit={handleEdit} className="flex gap-2 mt-1">
            <input
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="flex-1 bg-black/40 border border-[var(--border-glow)] rounded px-2 py-1
                         text-sm font-mono text-[var(--text-primary)] focus:outline-none"
              autoFocus
            />
            <button type="submit" className="text-xs text-[var(--text-primary)] hover:glow-teal px-2">save</button>
            <button type="button" onClick={() => setEditing(false)} className="text-xs text-[var(--text-muted)] px-2">cancel</button>
          </form>
        ) : (
          <p
            className={`text-sm leading-relaxed break-words whitespace-pre-wrap ${isOwn ? 'text-[var(--text-own)] glow-pink' : 'text-[var(--text-primary)] glow-teal'}`}
          >
            <MessageContent
              content={message.content}
              currentUsername={user?.username}
              isOwn={isOwn}
              onMentionClick={async (username) => {
                try {
                  const { data } = await getUserByUsername(username)
                  setProfileUserId(data.id)
                } catch { /* user not found — ignore */ }
              }}
            />
          </p>
        )}

        <Attachments attachments={message.attachments} />
        <ReactionBar reactions={message.reactions} messageId={message.id} />
      </div>

      {/* Hover actions */}
      {showActions && !editing && (
        <div className="relative flex items-start gap-1 flex-shrink-0">
          {/* Quick-react presets */}
          {['👍', '❤️', '😂', '🎉'].map((e) => (
            <button
              key={e}
              onClick={() => quickReact(e)}
              className="text-sm opacity-60 hover:opacity-100 hover:scale-125 transition-all"
              title={`React ${e}`}
            >
              {e}
            </button>
          ))}

          {/* Full emoji picker for reactions */}
          <button
            ref={reactionButtonRef}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => setShowReactionPicker((v) => !v)}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--accent-teal)] transition-colors px-1"
            title="Add reaction"
            data-testid="add-reaction-button"
          >
            +😊
          </button>

          {showReactionPicker && (
            <EmojiPicker
              onSelect={(emoji) => addReaction(message.id, emoji)}
              onClose={() => setShowReactionPicker(false)}
              anchorRef={reactionButtonRef}
              positionClass="bottom-full right-0"
            />
          )}

          <button
            onClick={() => setReplyingTo(message)}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors px-1"
            title="Reply"
            data-testid="reply-button"
          >
            ↩
          </button>
          {isOwn && (
            <>
              <button
                onClick={() => { setEditing(true); setEditContent(message.content) }}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors px-1"
                title="Edit"
              >
                ✎
              </button>
              <button
                onClick={handleDelete}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-error)] transition-colors px-1"
                title="Delete"
              >
                ✕
              </button>
            </>
          )}
        </div>
      )}
    </div>

    {profileUserId && (
      <ProfileModal userId={profileUserId} onClose={() => setProfileUserId(null)} />
    )}
    </>
  )
}
