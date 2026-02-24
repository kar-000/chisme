/**
 * useDMNotifications — global DM background listener.
 *
 * Maintains one WebSocket connection per DM channel that the user is NOT
 * currently viewing.  When a new message arrives from the other participant
 * it fires a browser notification.  The active DM (if any) is handled by
 * useWebSocketDM inside DMView; this hook covers the rest so users still get
 * notified while browsing a server channel.
 */
import { useEffect, useRef } from 'react'
import useDMStore from '../store/dmStore'
import useAuthStore from '../store/authStore'
import { showNotification } from '../utils/notifications'

export function useDMNotifications() {
  const token = useAuthStore((s) => s.token)
  const me = useAuthStore((s) => s.user)
  const dms = useDMStore((s) => s.dms)
  const activeDmId = useDMStore((s) => s.activeDmId)
  const appendDMMessage = useDMStore((s) => s.appendDMMessage)
  // Map of dm_id -> WebSocket
  const wsRefs = useRef({})

  useEffect(() => {
    if (!token || !me) return

    const currentIds = new Set(dms.map((d) => d.id))

    // Open connections for DMs not currently active and not yet connected
    dms.forEach((dm) => {
      if (dm.id === activeDmId) return  // DMView's useWebSocketDM handles this
      if (wsRefs.current[dm.id]) return  // already open

      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/dm/${dm.id}`)
      wsRefs.current[dm.id] = ws

      ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }))

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data)
          if (data.type === 'message.new' && data.message?.user_id !== me.id) {
            appendDMMessage(data.message)
            showNotification(`DM from ${data.message?.user?.username}`, {
              body: data.message?.content,
              tag: `dm-${data.message?.id}`,
            })
          }
        } catch { /* ignore parse errors */ }
      }

      ws.onclose = () => { delete wsRefs.current[dm.id] }
      ws.onerror = () => ws.close()
    })

    // Close connections for DMs that no longer exist or became active
    Object.keys(wsRefs.current).forEach((idStr) => {
      const id = Number(idStr)
      if (!currentIds.has(id) || id === activeDmId) {
        wsRefs.current[id]?.close()
        delete wsRefs.current[id]
      }
    })
  }, [token, me, dms, activeDmId, appendDMMessage])

  // Close all connections on logout / unmount
  useEffect(() => {
    return () => {
      Object.values(wsRefs.current).forEach((ws) => ws.close())
      wsRefs.current = {}
    }
  }, [])
}
