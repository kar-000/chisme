import useChatStore from '../../store/chatStore'

export default function Header({ onBack }) {
  const { channels, activeChannelId } = useChatStore()
  const channel = channels.find((c) => c.id === activeChannelId)

  if (!channel) return null

  return (
    <header className="px-6 py-4 border-b border-[var(--border)] bg-black/20 flex items-center gap-3 flex-shrink-0">
      <button
        onClick={onBack}
        className="md:hidden text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg transition-colors flex-shrink-0"
        title="Back to channels"
      >
        ←
      </button>
      <div>
        <h2 className="text-lg font-medium text-[var(--text-primary)] glow-teal">
          <span className="text-[var(--text-muted)]"># </span>{channel.name}
        </h2>
        {channel.description && (
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{channel.description}</p>
        )}
      </div>
    </header>
  )
}
