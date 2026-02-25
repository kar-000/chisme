import useDMStore from '../../store/dmStore'

export default function DMList({ onSelect }) {
  const { dms, activeDmId, unreadDmCounts } = useDMStore()

  if (!dms.length) {
    return (
      <p className="px-4 py-2 text-[10px] text-[var(--text-muted)] font-mono italic">
        no direct messages yet
      </p>
    )
  }

  return (
    <ul className="space-y-0.5 px-2">
      {dms.map((dm) => (
        <li key={dm.id}>
          <button
            onClick={() => onSelect?.(dm.id)}
            className={`
              w-full text-left px-3 py-1.5 rounded text-sm font-mono truncate transition-colors duration-150
              flex items-center justify-between
              ${activeDmId === dm.id
                ? 'bg-[var(--bg-active)] text-[var(--text-primary)] shadow-glow-sm'
                : 'text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
              }
            `}
            data-testid={`dm-item-${dm.id}`}
          >
            <span className="truncate">
              <span className="mr-1.5 opacity-60">@</span>
              {dm.other_user?.username}
            </span>
            {unreadDmCounts[dm.id] > 0 && (
              <span className="ml-2 min-w-[1.1rem] h-[1.1rem] flex items-center justify-center rounded-full bg-[var(--accent)] text-white text-[10px] font-bold shrink-0">
                {unreadDmCounts[dm.id] > 99 ? '99+' : unreadDmCounts[dm.id]}
              </span>
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}
