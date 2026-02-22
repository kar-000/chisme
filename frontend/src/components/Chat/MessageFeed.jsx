import { useEffect, useRef } from 'react'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'
import { useWebSocket } from '../../hooks/useWebSocket'
import Message from './Message'
import MessageSkeleton from './MessageSkeleton'
import MessageInput from './MessageInput'
import TypingIndicator from './TypingIndicator'
import Header from '../Layout/Header'
import FailoverBanner from '../Common/FailoverBanner'
import VoiceControls from '../Voice/VoiceControls'

export default function MessageFeed({ onBack }) {
  const { messages, loadingMessages, activeChannelId } = useChatStore()
  const { token, user } = useAuthStore()
  const bottomRef = useRef(null)

  const { sendTyping, sendMsg, connected, reconnecting, failoverDetected } = useWebSocket(activeChannelId, token)

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
      <FailoverBanner reconnecting={reconnecting} failoverDetected={failoverDetected} />
      <Header onBack={onBack} />

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
      <VoiceControls channelId={activeChannelId} currentUser={user} sendMsg={sendMsg} connected={connected} />
      <MessageInput onTyping={sendTyping} />
    </div>
  )
}
