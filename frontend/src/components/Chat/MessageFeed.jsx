import { useState, useEffect, useRef } from 'react'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'
import useServerStore from '../../store/serverStore'
import { useWebSocket } from '../../hooks/useWebSocket'
import Message from './Message'
import MessageSkeleton from './MessageSkeleton'
import MessageInput from './MessageInput'
import TypingIndicator from './TypingIndicator'
import ChannelNotes from './ChannelNotes'
import Header from '../Layout/Header'
import FailoverBanner from '../Common/FailoverBanner'

export default function MessageFeed({ onBack, onBookmarksOpen }) {
  const { messages, loadingMessages, activeChannelId } = useChatStore()
  const { token } = useAuthStore()
  const activeServerId = useServerStore((s) => s.activeServerId)
  const bottomRef = useRef(null)
  const [notesOpen, setNotesOpen] = useState(false)

  const { sendTyping, sendMsg, connected, reconnecting, failoverDetected } = useWebSocket(activeServerId, token)

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Close notes when switching channels
  useEffect(() => {
    setNotesOpen(false)
  }, [activeChannelId])

  if (!activeChannelId) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--text-muted)] font-mono">
        <p>← select a channel</p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0">
      <FailoverBanner reconnecting={reconnecting} failoverDetected={failoverDetected} />
      <Header
        onBack={onBack}
        onBookmarksOpen={onBookmarksOpen}
        notesOpen={notesOpen}
        onNotesToggle={() => setNotesOpen((o) => !o)}
      />

      <ChannelNotes channelId={activeChannelId} open={notesOpen} />

      {/* Messages scroll area */}
      <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-0.5 min-h-0">
        {loadingMessages && <MessageSkeleton />}
        {!loadingMessages && messages.length === 0 && (
          <p className="text-center text-xs text-[var(--text-muted)] py-8">
            No messages yet. Say something!
          </p>
        )}
        {messages.map((m) => (
          <Message key={m.id} message={m} />
        ))}
        <div ref={bottomRef} />
      </div>

      <TypingIndicator />
      <MessageInput onTyping={sendTyping} />
    </div>
  )
}
