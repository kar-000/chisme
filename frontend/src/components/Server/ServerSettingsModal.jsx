import { useRef, useState } from 'react'
import useServerStore from '../../store/serverStore'
import { uploadServerIcon } from '../../services/servers'
import { InviteForm } from './InviteForm'

function AppearanceTab({ server }) {
  const updateServer = useServerStore((s) => s.updateServer)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  const initials = server?.name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const { data } = await uploadServerIcon(server.id, file)
      updateServer(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Upload failed')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="server-settings-modal__section">
      <h3>Appearance</h3>
      <p className="server-settings-modal__description">
        Upload a custom icon for {server?.name}. JPEG, PNG, GIF, or WebP — max 5 MB.
      </p>

      <div className="flex items-center gap-5 mt-4">
        {/* Icon preview */}
        <div className="relative flex-shrink-0">
          {server?.icon_url ? (
            <img
              src={server.icon_url}
              alt={server.name}
              className="w-20 h-20 rounded-xl object-cover border-2 border-[var(--border-glow)]"
            />
          ) : (
            <div
              className="w-20 h-20 rounded-xl flex items-center justify-center text-2xl font-bold
                         bg-gradient-to-br from-crt-teal to-crt-teal-lt text-crt-bg shadow-glow-sm"
            >
              {initials}
            </div>
          )}
          {uploading && (
            <div className="absolute inset-0 rounded-xl bg-black/60 flex items-center justify-center">
              <span className="text-xs text-[var(--accent-teal)] font-mono animate-pulse">…</span>
            </div>
          )}
        </div>

        {/* Upload controls */}
        <div className="flex flex-col gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2 text-sm font-mono rounded border border-[var(--border-glow)]
                       text-[var(--accent-teal)] hover:bg-[var(--bg-hover)]
                       disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            type="button"
          >
            {uploading ? 'Uploading…' : 'Upload new icon'}
          </button>
          {error && (
            <p className="text-xs font-mono text-[var(--text-error)]">&gt; {error}</p>
          )}
        </div>
      </div>
    </div>
  )
}

export function ServerSettingsModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('appearance')
  const activeServerId = useServerStore((s) => s.activeServerId)
  const servers = useServerStore((s) => s.servers)
  const server = servers.find((s) => s.id === activeServerId)

  const tabs = [
    { id: 'appearance', label: 'Appearance' },
    { id: 'invite', label: 'Invite People' },
  ]

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
          {activeTab === 'appearance' && <AppearanceTab server={server} />}
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
