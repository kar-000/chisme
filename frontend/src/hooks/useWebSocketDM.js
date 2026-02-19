import { useEffect, useRef, useCallback } from 'react'
import useDMStore from '../store/dmStore'

const RECONNECT_DELAY = 3000

export function useWebSocketDM(dmId, token) {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const appendDMMessage = useDMStore((s) => s.appendDMMessage)

  const connect = useCallback(() => {
    if (!dmId || !token) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}/ws/dm/${dmId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', token }))
    }

    ws.onmessage = (ev) => {
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      if (data.type === 'message.new') {
        appendDMMessage(data.message)
      }
    }

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = () => ws.close()
  }, [dmId, token, appendDMMessage])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])
}
