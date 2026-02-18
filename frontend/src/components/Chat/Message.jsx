import { useState } from 'react'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'

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
            <span>{emoji}</span>
            <span className="text-[var(--text-muted)] font-mono">{count}</span>
          </button>
        )
      })}
    </div>
  )
}

export default function Message({ message }) {
  const { user } = useAuthStore()
  const { editMessage, deleteMessage, addReaction } = useChatStore()
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.content)
  const [showActions, setShowActions] = useState(false)

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
    <div
      className={`
        group flex gap-3 px-3 py-2 rounded transition-all duration-150 msg-appear
        ${isOwn ? 'bg-[rgba(255,182,193,0.06)]' : 'hover:bg-[rgba(0,206,209,0.04)]'}
      `}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div
        className="w-8 h-8 rounded flex-shrink-0 flex items-center justify-center
                   text-[10px] font-bold bg-gradient-to-br from-crt-teal to-crt-teal-lt
                   text-crt-bg shadow-glow-sm mt-0.5"
      >
        {message.user?.username?.slice(0, 2).toUpperCase()}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-0.5">
          <span
            className={`text-sm font-medium ${isOwn ? 'text-[var(--text-lt)]' : 'text-[var(--text-lt)]'}`}
            style={{ textShadow: '0 0 4px rgba(93,173,226,0.4)' }}
          >
            {message.user?.username}
          </span>
          <span className="text-[10px] text-[var(--text-muted)]">
            {formatTime(message.created_at)}
          </span>
          {message.edited_at && (
            <span className="text-[10px] text-[var(--text-muted)] italic">(edited)</span>
          )}
        </div>

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
            className={`text-sm leading-relaxed break-words ${isOwn ? 'text-[var(--text-own)] glow-pink' : 'text-[var(--text-primary)] glow-teal'}`}
          >
            {message.content}
          </p>
        )}

        <ReactionBar reactions={message.reactions} messageId={message.id} />
      </div>

      {/* Hover actions */}
      {showActions && !editing && (
        <div className="flex items-start gap-1 flex-shrink-0">
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
  )
}
