/**
 * useVoiceWebSocket — persistent WebSocket connection to /ws/voice.
 *
 * Unlike the channel WebSocket this connection is NOT tied to any text
 * channel.  It stays open for the lifetime of the ChatLayout and
 * survives text-channel switches, so voice state is never interrupted
 * by navigation.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import useChatStore from '../store/chatStore'

const MAX_RECONNECT_ATTEMPTS = 10

function getBackoffDelay(attempt) {
  return Math.min(1000 * Math.pow(2, attempt), 30000)
}

export function useVoiceWebSocket(token) {
  const [connected, setConnected] = useState(false)

  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const attemptsRef = useRef(0)
  const mountedRef = useRef(true)

  const setVoiceSnapshot = useChatStore((s) => s.setVoiceSnapshot)
  const setVoiceUser = useChatStore((s) => s.setVoiceUser)
  const removeVoiceUser = useChatStore((s) => s.removeVoiceUser)
  const pushVoiceSignal = useChatStore((s) => s.pushVoiceSignal)

  const sendVoiceMsg = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  const connect = useCallback(() => {
    if (!token) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/voice`)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      ws.send(JSON.stringify({ type: 'auth', token }))
      setConnected(true)
      attemptsRef.current = 0
    }

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      switch (data.type) {
        case 'voice.state_snapshot':
          // Atomically replace state — clears anyone who left during a disconnect
          setVoiceSnapshot(data.users)
          break
        case 'voice.user_joined':
          setVoiceUser(data.user_id, {
            user_id: data.user_id,
            username: data.username,
            muted: data.muted,
            video: data.video,
          })
          break
        case 'voice.user_left':
          removeVoiceUser(data.user_id)
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

    ws.onclose = () => {
      if (!mountedRef.current) return
      setConnected(false)
      if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = getBackoffDelay(attemptsRef.current)
        attemptsRef.current++
        reconnectTimer.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => ws.close()
  }, [token, setVoiceSnapshot, setVoiceUser, removeVoiceUser, pushVoiceSignal])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { sendVoiceMsg, voiceConnected: connected }
}
