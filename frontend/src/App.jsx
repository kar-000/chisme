import { useEffect, useState } from 'react'
import useAuthStore from './store/authStore'
import useChatStore from './store/chatStore'
import useDMStore from './store/dmStore'
import AuthPage from './components/Auth/AuthPage'
import Sidebar from './components/Layout/Sidebar'
import MessageFeed from './components/Chat/MessageFeed'
import DMView from './components/Chat/DMView'
import MessageSearch from './components/Common/MessageSearch'
import ShortcutsModal from './components/Common/ShortcutsModal'
import ErrorBoundary from './components/Common/ErrorBoundary'

function ChatLayout() {
  const fetchChannels = useChatStore((s) => s.fetchChannels)
  const activeDmId = useDMStore((s) => s.activeDmId)
  const [searchOpen, setSearchOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen((v) => !v)
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault()
        setShortcutsOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <ErrorBoundary>
      <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
        <Sidebar onSearchOpen={() => setSearchOpen(true)} />
        <ErrorBoundary>
          {activeDmId ? <DMView /> : <MessageFeed />}
        </ErrorBoundary>
        {searchOpen && <MessageSearch onClose={() => setSearchOpen(false)} />}
        {shortcutsOpen && <ShortcutsModal onClose={() => setShortcutsOpen(false)} />}
      </div>
    </ErrorBoundary>
  )
}

export default function App() {
  const { user, token, loadUser } = useAuthStore()

  useEffect(() => {
    if (token && !user) loadUser()
  }, [token, user, loadUser])

  if (!token) return <AuthPage />

  // Still resolving user from token
  if (token && !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-[var(--bg-primary)] text-[var(--text-muted)] font-mono">
        Connecting…
      </div>
    )
  }

  return <ChatLayout />
}
