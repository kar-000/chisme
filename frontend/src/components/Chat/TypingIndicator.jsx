import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'

export default function TypingIndicator() {
  const typingUsers = useChatStore((s) => s.typingUsers)
  const { user } = useAuthStore()
  const others = typingUsers.filter((u) => u !== user?.username)

  if (!others.length) return null

  const label =
    others.length === 1
      ? `${others[0]} is typing`
      : `${others.slice(0, -1).join(', ')} and ${others.at(-1)} are typing`

  return (
    <div className="px-4 pb-1 text-xs text-[var(--text-muted)] italic flex items-center gap-1">
      {label}
      <span className="flex gap-0.5 ml-1">
        {[0, 0.2, 0.4].map((d, i) => (
          <span
            key={i}
            className="w-1 h-1 rounded-full bg-[var(--text-muted)]"
            style={{ animation: `typing-blink 1.4s ${d}s infinite both` }}
          />
        ))}
      </span>
    </div>
  )
}
