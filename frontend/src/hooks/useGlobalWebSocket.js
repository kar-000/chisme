/**
 * useGlobalWebSocket — one persistent notification connection per user session.
 *
 * Connects to /ws/global at login and stays alive for the entire session,
 * regardless of which server or channel is currently being viewed.  The
 * backend pushes two event types here:
 *
 *   notification     — a channel message the user should be notified about
 *   dm.message.new   — an incoming DM (data + notification in one payload)
 *
 * This hook replaces useDMNotifications and removes the need for N background
 * DM WebSocket connections.
 *
 * A module-level getter `isGlobalWsConnected()` is exported so that
 * useWebSocket.js can fall back to showing in-server notifications when the
 * global WS is mid-reconnect (transient network dropout).
 */

import { useEffect, useRef } from 'react'
import useChatStore from '../store/chatStore'
import useDMStore from '../store/dmStore'
import useServerStore from '../store/serverStore'
import { showNotification } from '../utils/notifications'

const MAX_RECONNECT_ATTEMPTS = 10

function getBackoffDelay(attempt) {
  return Math.min(1000 * Math.pow(2, attempt), 30000)
}

// Module-level flag so useWebSocket.js can check connectivity without prop-drilling.
let _globalConnected = false
export const isGlobalWsConnected = () => _globalConnected

export function useGlobalWebSocket(token) {
  const wsRef = useRef(null)
  const mountedRef = useRef(true)
  const attemptsRef = useRef(0)
  const reconnectTimer = useRef(null)

  useEffect(() => {
    mountedRef.current = true
    attemptsRef.current = 0

    function connect() {
      if (!token || !mountedRef.current) return
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/global`)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current || wsRef.current !== ws) { ws.close(); return }
        ws.send(JSON.stringify({ type: 'auth', token }))
        _globalConnected = true
        attemptsRef.current = 0
      }

      ws.onmessage = (ev) => {
        if (!mountedRef.current || wsRef.current !== ws) return
        let data
        try { data = JSON.parse(ev.data) } catch { return }

        switch (data.type) {
          case 'notification': {
            // Suppress if the user is already looking at this exact channel.
            const { activeChannelId } = useChatStore.getState()
            const { activeServerId } = useServerStore.getState()
            if (data.channel_id === activeChannelId && data.server_id === activeServerId) break
            showNotification(data.title, { body: data.body, tag: data.tag })
            break
          }

          case 'dm.message.new': {
            // Suppress data append + notification if the DM is currently active
            // (DMView's useWebSocketDM already handles the active DM).
            const { activeDmId, appendDMMessage, incrementDmUnread } = useDMStore.getState()
            if (data.dm_id === activeDmId) break
            if (data.message) appendDMMessage(data.message)
            incrementDmUnread(data.dm_id)
            showNotification(data.title, { body: data.body, tag: `dm-${data.message?.id}` })
            break
          }

          default:
            break
        }
      }

      ws.onclose = () => {
        if (!mountedRef.current || wsRef.current !== ws) return
        _globalConnected = false
        if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectTimer.current = setTimeout(connect, getBackoffDelay(attemptsRef.current++))
        }
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      mountedRef.current = false
      _globalConnected = false
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [token])
}
