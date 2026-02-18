import { useEffect } from 'react'
import useAuthStore from './store/authStore'
import useChatStore from './store/chatStore'
import AuthPage from './components/Auth/AuthPage'
import Sidebar from './components/Layout/Sidebar'
import MessageFeed from './components/Chat/MessageFeed'

function ChatLayout() {
  const fetchChannels = useChatStore((s) => s.fetchChannels)

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      <Sidebar />
      <MessageFeed />
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
