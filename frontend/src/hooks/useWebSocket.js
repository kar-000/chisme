import { useState, useEffect, useRef, useCallback } from 'react'
import useChatStore from '../store/chatStore'

const MAX_RECONNECT_ATTEMPTS = 10

function getBackoffDelay(attempt) {
  // Exponential backoff: 1s, 2s, 4s, 8s … capped at 30s
  return Math.min(1000 * Math.pow(2, attempt), 30000)
}

export function useWebSocket(channelId, token) {
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [failoverDetected, setFailoverDetected] = useState(false)

  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const failoverClearTimer = useRef(null)
  const attemptsRef = useRef(0)
  const mountedRef = useRef(true)

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
      if (!mountedRef.current) return
      ws.send(JSON.stringify({ type: 'auth', token }))
      setConnected(true)
      setReconnecting(false)
      attemptsRef.current = 0
      // Keep "back online" banner for 5s then clear
      clearTimeout(failoverClearTimer.current)
      failoverClearTimer.current = setTimeout(() => {
        if (mountedRef.current) setFailoverDetected(false)
      }, 5000)
    }

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return
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

    ws.onclose = (ev) => {
      if (!mountedRef.current) return
      setConnected(false)
      // Abnormal closure or server going away may indicate failover
      if (ev?.code === 1006 || ev?.code === 1001) {
        setFailoverDetected(true)
      }
      // Schedule reconnect with exponential backoff
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
  }, [channelId, token, appendMessage, updateMessage, removeMessage, setTypingUsers])

  const sendTyping = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'user.typing' }))
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

  return { sendTyping, connected, reconnecting, failoverDetected }
}
