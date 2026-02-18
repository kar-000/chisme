import { useEffect, useRef, useCallback } from 'react'
import useChatStore from '../store/chatStore'

const RECONNECT_DELAY = 3000

export function useWebSocket(channelId, token) {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const appendMessage = useChatStore((s) => s.appendMessage)
  const updateMessage = useChatStore((s) => s.updateMessage)
  const removeMessage = useChatStore((s) => s.removeMessage)
  const setTypingUsers = useChatStore((s) => s.setTypingUsers)
  const typingTimeouts = useRef({})

  const connect = useCallback(() => {
    if (!channelId || !token) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}/ws/channels/${channelId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', token }))
    }

    ws.onmessage = (ev) => {
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      switch (data.type) {
        case 'message.new':
          appendMessage(data.message)
          break
        case 'message.updated':
          updateMessage(data.message)
          break
        case 'message.deleted':
          removeMessage(data.message_id)
          break
        case 'user.typing': {
          const { username } = data
          setTypingUsers((prev) => [...new Set([...prev, username])])
          clearTimeout(typingTimeouts.current[username])
          typingTimeouts.current[username] = setTimeout(() => {
            setTypingUsers((prev) => prev.filter((u) => u !== username))
          }, 3000)
          break
        }
        default:
          break
      }
    }

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = () => ws.close()
  }, [channelId, token, appendMessage, updateMessage, removeMessage, setTypingUsers])

  // Send typing event
  const sendTyping = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'user.typing' }))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { sendTyping }
}
