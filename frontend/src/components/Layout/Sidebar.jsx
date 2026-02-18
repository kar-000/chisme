import ChannelList from '../Chat/ChannelList'
import useAuthStore from '../../store/authStore'

function Avatar({ username }) {
  const initials = username?.slice(0, 2).toUpperCase() ?? '??'
  return (
    <div className="w-8 h-8 rounded flex items-center justify-center text-xs font-bold
                    bg-gradient-to-br from-crt-teal to-crt-teal-lt text-crt-bg shadow-glow-sm flex-shrink-0">
      {initials}
    </div>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuthStore()

  return (
    <aside className="w-60 flex flex-col bg-black/20 border-r border-[var(--border)] flex-shrink-0">
      {/* App title */}
      <div className="px-4 py-5 border-b border-[var(--border)]">
        <h1 className="text-2xl font-bold tracking-widest text-[var(--text-primary)] glow-teal">
          chisme
        </h1>
        <p className="text-[10px] text-[var(--text-muted)] tracking-wider mt-0.5">
          warm crt chat
        </p>
      </div>

      {/* Channel list */}
      <div className="flex-1 min-h-0 py-2">
        <ChannelList />
      </div>

      {/* User panel */}
      <div className="px-3 py-3 border-t border-[var(--border)] flex items-center gap-2">
        <Avatar username={user?.username} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)] truncate">{user?.username}</p>
          <p className="text-[10px] text-[var(--text-muted)] truncate">{user?.status}</p>
        </div>
        <button
          onClick={logout}
          title="Sign out"
          className="text-[var(--text-muted)] hover:text-[var(--text-error)] text-xs transition-colors flex-shrink-0"
        >
          ⏻
        </button>
      </div>
    </aside>
  )
}
