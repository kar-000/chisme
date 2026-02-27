import { useState, useRef, useEffect } from 'react'
import useNotificationStore from '../../store/notificationStore'
import useServerStore from '../../store/serverStore'
import { useInviteModal } from '../../hooks/useInviteModal'

export function ServerIcon({ server, isActive, onClick }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 })
  const menuRef = useRef(null)
  const invite = useInviteModal()
  const setActiveServer = useServerStore((s) => s.setActiveServer)
  const clearServerNotification = useNotificationStore((s) => s.clearServerNotification)
  const notifType = useNotificationStore((s) => s.serverNotifications[server.id] ?? null)

  const notifColor =
    notifType === 'mention'
      ? 'var(--accent-orange)'
      : notifType === 'message'
        ? 'var(--accent-teal)'
        : null
  const notifStyle = notifColor
    ? {
        outline: `2px solid ${notifColor}`,
        outlineOffset: '2px',
        boxShadow: `0 0 10px ${notifColor}`,
        transition: 'outline 0.2s ease, box-shadow 0.2s ease',
      }
    : {}

  const canInvite =
    server.current_user_role === 'owner' || server.current_user_role === 'admin'

  const handleContextMenu = (e) => {
    e.preventDefault()
    setMenuPos({ x: e.clientX, y: e.clientY })
    setMenuOpen(true)
  }

  useEffect(() => {
    if (!menuOpen) return
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const initials = server.name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')

  return (
    <>
      <button
        className={`server-icon${isActive ? ' server-icon--active' : ''}`}
        onClick={onClick}
        onContextMenu={handleContextMenu}
        title={server.name}
        type="button"
        style={notifStyle}
      >
        {server.icon_url ? (
          <img src={server.icon_url} alt={server.name} />
        ) : (
          <span className="server-icon__initials">{initials}</span>
        )}
      </button>

      {menuOpen && (
        <div
          ref={menuRef}
          className="server-context-menu"
          style={{ top: menuPos.y, left: menuPos.x }}
        >
          <div className="server-context-menu__label">{server.name}</div>
          <div className="server-context-menu__divider" />
          {canInvite && (
            <button
              className="server-context-menu__item"
              type="button"
              onClick={() => {
                setActiveServer(server.id)
                clearServerNotification(server.id)
                setMenuOpen(false)
                invite.open()
              }}
            >
              Invite People
            </button>
          )}
          <button
            className="server-context-menu__item"
            type="button"
            onClick={() => {
              setActiveServer(server.id)
              clearServerNotification(server.id)
              setMenuOpen(false)
            }}
          >
            Switch to Server
          </button>
        </div>
      )}
    </>
  )
}
