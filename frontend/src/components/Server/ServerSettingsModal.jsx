import { useState } from 'react'
import useServerStore from '../../store/serverStore'
import { InviteForm } from './InviteForm'

export function ServerSettingsModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('invite')
  const activeServerId = useServerStore((s) => s.activeServerId)
  const servers = useServerStore((s) => s.servers)
  const server = servers.find((s) => s.id === activeServerId)

  const tabs = [{ id: 'invite', label: 'Invite People' }]

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="server-settings-modal">
        <div className="server-settings-modal__sidebar">
          <div className="server-settings-modal__server-name">{server?.name}</div>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`server-settings-modal__tab${activeTab === tab.id ? ' server-settings-modal__tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
          <div className="server-settings-modal__divider" />
          <button className="server-settings-modal__close-btn" onClick={onClose} type="button">
            ✕ Close
          </button>
        </div>

        <div className="server-settings-modal__content">
          {activeTab === 'invite' && (
            <div className="server-settings-modal__section">
              <h3>Invite People</h3>
              <p className="server-settings-modal__description">
                Generate a link to share with anyone you want to invite to {server?.name}. You can
                set a usage limit and expiry time.
              </p>
              <InviteForm serverId={activeServerId} serverName={server?.name} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
