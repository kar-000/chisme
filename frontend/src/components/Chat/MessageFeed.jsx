import { useEffect, useRef } from 'react'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'
import { useWebSocket } from '../../hooks/useWebSocket'
import Message from './Message'
import MessageInput from './MessageInput'
import TypingIndicator from './TypingIndicator'
import Header from '../Layout/Header'

export default function MessageFeed() {
  const { messages, loadingMessages, activeChannelId } = useChatStore()
  const { token } = useAuthStore()
  const bottomRef = useRef(null)

  const { sendTyping } = useWebSocket(activeChannelId, token)

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!activeChannelId) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--text-muted)] font-mono">
        <p>← select a channel</p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0">
      <Header />

      {/* Messages scroll area */}
      <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-0.5 min-h-0">
        {loadingMessages && (
          <p className="text-center text-xs text-[var(--text-muted)] py-4">Loading…</p>
        )}
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
