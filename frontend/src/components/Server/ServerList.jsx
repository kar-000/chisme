import useNotificationStore from '../../store/notificationStore'
import useServerStore from '../../store/serverStore'
import { AddServerButton } from './AddServerButton'
import { ServerIcon } from './ServerIcon'

export function ServerList() {
  const servers = useServerStore((s) => s.servers)
  const activeServerId = useServerStore((s) => s.activeServerId)
  const setActiveServer = useServerStore((s) => s.setActiveServer)
  const clearServerNotification = useNotificationStore((s) => s.clearServerNotification)

  return (
    <nav className="server-list" aria-label="Servers">
      {servers.map((server) => (
        <ServerIcon
          key={server.id}
          server={server}
          isActive={server.id === activeServerId}
          onClick={() => {
            setActiveServer(server.id)
            clearServerNotification(server.id)
          }}
        />
      ))}
      <div className="server-list__divider" />
      <AddServerButton />
    </nav>
  )
}
