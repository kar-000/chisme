import { useEffect, useState } from 'react'
import useAuthStore from './store/authStore'
import useChatStore from './store/chatStore'
import useDMStore from './store/dmStore'
import AuthPage from './components/Auth/AuthPage'
import Sidebar from './components/Layout/Sidebar'
import MessageFeed from './components/Chat/MessageFeed'
import DMView from './components/Chat/DMView'
import MessageSearch from './components/Common/MessageSearch'

function ChatLayout() {
  const fetchChannels = useChatStore((s) => s.fetchChannels)
  const activeDmId = useDMStore((s) => s.activeDmId)
  const [searchOpen, setSearchOpen] = useState(false)

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  // Global Ctrl+K shortcut
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      <Sidebar onSearchOpen={() => setSearchOpen(true)} />
      {activeDmId ? <DMView /> : <MessageFeed />}
      {searchOpen && <MessageSearch onClose={() => setSearchOpen(false)} />}
    </div>
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
