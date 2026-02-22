import { useEffect, useState } from 'react'
import useAuthStore from './store/authStore'
import useChatStore from './store/chatStore'
import useServerStore from './store/serverStore'
import useDMStore from './store/dmStore'
import AuthPage from './components/Auth/AuthPage'
import Sidebar from './components/Layout/Sidebar'
import MessageFeed from './components/Chat/MessageFeed'
import DMView from './components/Chat/DMView'
import VoiceControls from './components/Voice/VoiceControls'
import MessageSearch from './components/Common/MessageSearch'
import ShortcutsModal from './components/Common/ShortcutsModal'
import ErrorBoundary from './components/Common/ErrorBoundary'
import { ServerList } from './components/Server/ServerList'
import { InviteLandingPage } from './pages/InviteLandingPage'
import { OperatorDashboard } from './pages/OperatorDashboard'
import { useFaviconBadge } from './hooks/useFaviconBadge'
import { useVoiceWebSocket } from './hooks/useVoiceWebSocket'

// Detect special routes at module load time (before any React rendering)
const pathname = window.location.pathname

function ChatLayout() {
  useFaviconBadge()
  const { token, user } = useAuthStore()
  const fetchServers = useServerStore((s) => s.fetchServers)
  const activeDmId = useDMStore((s) => s.activeDmId)
  const [searchOpen, setSearchOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const { sendVoiceMsg, voiceConnected } = useVoiceWebSocket(token)

  const handleNavigate = () => setSidebarOpen(false)
  const handleBack = () => setSidebarOpen(true)

  // Fetch the server list on login; fetchServers auto-selects the first
  // server and triggers fetchChannels via serverStore.setActiveServer.
  useEffect(() => {
    fetchServers()
  }, [fetchServers])

  // Check for a pending invite code stored before a login redirect
  useEffect(() => {
    const pendingCode = sessionStorage.getItem('pendingInviteCode')
    if (pendingCode) {
      sessionStorage.removeItem('pendingInviteCode')
      window.history.replaceState({}, '', `/invite/${pendingCode}`)
    }
  }, [])

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
      <div
        className="flex overflow-hidden bg-[var(--bg-primary)]"
        style={{ height: '100dvh' }}
      >
        {/* Server list column — leftmost, 64px wide */}
        <ServerList />

        {/* Channel sidebar */}
        <Sidebar
          onSearchOpen={() => setSearchOpen(true)}
          onNavigate={handleNavigate}
          mobileHidden={!sidebarOpen}
        />

        {/* Main content area */}
        <div
          className={`${sidebarOpen ? 'hidden md:flex' : 'flex'} flex-1 flex-col min-w-0 min-h-0`}
        >
          <ErrorBoundary>
            {activeDmId ? (
              <DMView onBack={handleBack} />
            ) : (
              <MessageFeed onBack={handleBack} />
            )}
          </ErrorBoundary>
          <VoiceControls
            currentUser={user}
            sendMsg={sendVoiceMsg}
            connected={voiceConnected}
          />
        </div>

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

  // Handle /invite/{code}
  if (pathname.startsWith('/invite/')) {
    if (!token) {
      // Not logged in: store the code and fall through to show AuthPage
      const code = pathname.split('/').pop()
      if (code) sessionStorage.setItem('pendingInviteCode', code)
      // Will fall through to the !token return below
    } else if (token && user) {
      return <InviteLandingPage />
    }
    // If token but no user yet, fall through to the loading screen below
  }

  // Handle /operator
  if (pathname === '/operator') {
    if (!token) {
      window.history.replaceState({}, '', '/')
      return null
    }
    if (token && user) {
      return <OperatorDashboard />
    }
    // Loading state falls through below
  }

  if (!token) return <AuthPage />

  // Token present but user not yet resolved from it
  if (token && !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-[var(--bg-primary)] text-[var(--text-muted)] font-mono">
        Connecting…
      </div>
    )
  }

  return <ChatLayout />
}
