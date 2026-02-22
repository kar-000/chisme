import { useState, useEffect, useRef, useCallback } from 'react'
import useChatStore from '../store/chatStore'
import useAuthStore from '../store/authStore'
import { isMention, requestNotificationPermission, showNotification } from '../utils/notifications'

const MAX_RECONNECT_ATTEMPTS = 10

function getBackoffDelay(attempt) {
  return Math.min(1000 * Math.pow(2, attempt), 30000)
}

/**
 * Opens a server-level WebSocket connection at /ws/server/{serverId}.
 * A single connection per server carries all channel text events, typing
 * indicators, presence, and voice signaling.  Each payload includes a
 * channel_id field so the frontend can route it to the correct channel.
 */
export function useWebSocket(serverId, token) {
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [failoverDetected, setFailoverDetected] = useState(false)

  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const failoverClearTimer = useRef(null)
  const attemptsRef = useRef(0)
  const mountedRef = useRef(true)
  const notifPermRequested = useRef(false)

  const me = useAuthStore((s) => s.user)
  const appendMessageForChannel = useChatStore((s) => s.appendMessageForChannel)
  const incrementUnread = useChatStore((s) => s.incrementUnread)
  const updateMessage = useChatStore((s) => s.updateMessage)
  const removeMessage = useChatStore((s) => s.removeMessage)
  const setTypingUsers = useChatStore((s) => s.setTypingUsers)
  const setVoiceUser = useChatStore((s) => s.setVoiceUser)
  const removeVoiceUser = useChatStore((s) => s.removeVoiceUser)
  const pushVoiceSignal = useChatStore((s) => s.pushVoiceSignal)
  const setChannelVoiceCount = useChatStore((s) => s.setChannelVoiceCount)
  const adjustChannelVoiceCount = useChatStore((s) => s.adjustChannelVoiceCount)
  const typingTimeouts = useRef({})

  const connect = useCallback(() => {
    if (!serverId || !token) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}/ws/server/${serverId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      ws.send(JSON.stringify({ type: 'auth', token }))
      setConnected(true)
      setReconnecting(false)
      attemptsRef.current = 0
      if (!notifPermRequested.current) {
        notifPermRequested.current = true
        requestNotificationPermission()
      }
      clearTimeout(failoverClearTimer.current)
      failoverClearTimer.current = setTimeout(() => {
        if (mountedRef.current) setFailoverDetected(false)
      }, 5000)
    }

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      const channelId = data.channel_id
      const activeChannelId = useChatStore.getState().activeChannelId

      switch (data.type) {
        case 'message.new':
          if (channelId === activeChannelId) {
            appendMessageForChannel(channelId, data.message)
          } else {
            incrementUnread(channelId)
          }
          if (me && isMention(data.message?.content, me.username)) {
            showNotification(
              `@${me.username} mentioned by ${data.message?.user?.username}`,
              { body: data.message?.content, tag: `mention-${data.message?.id}` }
            )
          }
          break
        case 'message.updated':
          updateMessage(data.message)
          break
        case 'message.deleted':
          removeMessage(data.message_id)
          break
        case 'user.typing': {
          if (channelId !== activeChannelId) break
          const { username } = data
          setTypingUsers((prev) => [...new Set([...prev, username])])
          clearTimeout(typingTimeouts.current[username])
          typingTimeouts.current[username] = setTimeout(() => {
            setTypingUsers((prev) => prev.filter((u) => u !== username))
          }, 3000)
          break
        }
        case 'voice.state_snapshot':
          data.users.forEach((u) => setVoiceUser(u.user_id, u))
          setChannelVoiceCount(data.channel_id, data.users.length)
          break
        case 'voice.user_joined':
          setVoiceUser(data.user_id, {
            user_id: data.user_id,
            username: data.username,
            muted: data.muted,
            video: data.video,
          })
          adjustChannelVoiceCount(data.channel_id, 1)
          break
        case 'voice.user_left':
          removeVoiceUser(data.user_id)
          adjustChannelVoiceCount(data.channel_id, -1)
          break
        case 'voice.state_changed':
          setVoiceUser(data.user_id, {
            muted: data.muted,
            video: data.video,
            speaking: data.speaking ?? false,
          })
          break
        case 'voice.offer':
        case 'voice.answer':
        case 'voice.ice_candidate':
          pushVoiceSignal(data)
          break
        default:
          break
      }
    }

    ws.onclose = (ev) => {
      if (!mountedRef.current) return
      setConnected(false)
      if (ev?.code === 1006 || ev?.code === 1001) {
        setFailoverDetected(true)
      }
      if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = getBackoffDelay(attemptsRef.current)
        attemptsRef.current++
        setReconnecting(true)
        reconnectTimer.current = setTimeout(connect, delay)
      } else {
        setReconnecting(false)
      }
    }

    ws.onerror = () => ws.close()
  }, [
    serverId,
    token,
    appendMessageForChannel,
    incrementUnread,
    updateMessage,
    removeMessage,
    setTypingUsers,
    setVoiceUser,
    removeVoiceUser,
    pushVoiceSignal,
    setChannelVoiceCount,
    adjustChannelVoiceCount,
  ])

  // Send a typing indicator for the currently-active channel
  const sendTyping = useCallback((channelId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'user.typing', channel_id: channelId }))
    }
  }, [])

  const sendMsg = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    attemptsRef.current = 0
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimer.current)
      clearTimeout(failoverClearTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { sendTyping, sendMsg, connected, reconnecting, failoverDetected }
}
