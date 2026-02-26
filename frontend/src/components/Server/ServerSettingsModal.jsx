import { useRef, useState, useEffect } from 'react'
import useServerStore from '../../store/serverStore'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'
import { uploadServerIcon, listMembers } from '../../services/servers'
import { InviteForm } from './InviteForm'
import SetNicknameModal from './SetNicknameModal'

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

function MembersTab({ server, onClose }) {
  const me = useAuthStore((s) => s.user)
  const updateMemberRole = useServerStore((s) => s.updateMemberRole)
  const removeMember = useServerStore((s) => s.removeMember)
  const transferOwnership = useServerStore((s) => s.transferOwnership)
  const deleteServer = useServerStore((s) => s.deleteServer)
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmKick, setConfirmKick] = useState(null)
  const [confirmTransfer, setConfirmTransfer] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [working, setWorking] = useState(false)

  const isOwner = server?.current_user_role === 'owner'
  const isAdmin = server?.current_user_role === 'admin'

  useEffect(() => {
    if (!server?.id) return
    listMembers(server.id)
      .then(({ data }) => setMembers(data))
      .catch(() => setError('Failed to load members'))
      .finally(() => setLoading(false))
  }, [server?.id])

  const handleRoleChange = async (userId, newRole) => {
    try {
      await updateMemberRole(server.id, userId, newRole)
      setMembers((ms) => ms.map((m) => m.user_id === userId ? { ...m, role: newRole } : m))
    } catch {
      setError('Failed to update role')
    }
  }

  const handleKick = async () => {
    if (!confirmKick) return
    setWorking(true)
    try {
      await removeMember(server.id, confirmKick.user_id)
      setMembers((ms) => ms.filter((m) => m.user_id !== confirmKick.user_id))
      setConfirmKick(null)
    } catch {
      setError('Failed to remove member')
    } finally {
      setWorking(false)
    }
  }

  const handleTransfer = async () => {
    if (!confirmTransfer) return
    setWorking(true)
    try {
      await transferOwnership(server.id, confirmTransfer.user_id)
      // Refresh the member list (roles changed)
      const { data } = await listMembers(server.id)
      setMembers(data)
      setConfirmTransfer(null)
    } catch {
      setError('Failed to transfer ownership')
    } finally {
      setWorking(false)
    }
  }

  const handleDeleteServer = async () => {
    setWorking(true)
    try {
      await deleteServer(server.id)
      onClose()
    } catch {
      setError('Failed to delete server')
      setWorking(false)
      setConfirmDelete(false)
    }
  }

  return (
    <div className="server-settings-modal__section">
      <h3>Members</h3>
      {loading && <p className="text-xs font-mono text-[var(--text-muted)] mt-3">Loading…</p>}
      {error && <p className="text-xs font-mono text-[var(--text-error)] mt-2">&gt; {error}</p>}
      {!loading && (
        <ul className="mt-4 flex flex-col gap-1">
          {members.map((m) => {
            const isSelf = m.user_id === me?.id
            const isTheirOwner = m.role === 'owner'
            return (
              <li key={m.user_id} className="flex flex-wrap items-center gap-2 px-3 py-2 rounded
                                              bg-[var(--bg-hover)] text-sm">
                <span className="flex-1 min-w-0 font-mono text-[var(--text-primary)] truncate">
                  {m.display_name || m.username}
                  {isSelf && <span className="text-[var(--text-muted)] text-xs ml-1">(you)</span>}
                </span>
                {/* Role + action buttons grouped so they wrap together */}
                <div className="flex items-center gap-2 ml-auto flex-shrink-0">
                  {/* Role badge / selector */}
                  {(isOwner && !isSelf && !isTheirOwner) ? (
                    <select
                      value={m.role}
                      onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                      className="text-xs font-mono bg-[var(--bg-secondary)] border border-[var(--border)]
                                 text-[var(--text-muted)] rounded px-1 py-0.5 cursor-pointer"
                    >
                      <option value="member">member</option>
                      <option value="admin">admin</option>
                    </select>
                  ) : (
                    <span className={`text-xs font-mono px-1.5 py-0.5 rounded
                      ${isTheirOwner ? 'text-[var(--crt-orange)]' :
                        m.role === 'admin' ? 'text-[var(--accent-teal)]' :
                        'text-[var(--text-muted)]'}`}>
                      {m.role}
                    </span>
                  )}
                  {/* Transfer ownership */}
                  {isOwner && !isSelf && !isTheirOwner && (
                    <button
                      type="button"
                      title="Transfer ownership"
                      onClick={() => setConfirmTransfer(m)}
                      className="text-xs text-[var(--text-muted)] hover:text-[var(--crt-orange)]
                                 transition-colors font-mono"
                    >
                      crown
                    </button>
                  )}
                  {/* Kick */}
                  {(isOwner || isAdmin) && !isSelf && !isTheirOwner && (
                    <button
                      type="button"
                      title="Remove member"
                      onClick={() => setConfirmKick(m)}
                      className="text-xs text-[var(--text-muted)] hover:text-[var(--text-error)]
                                 transition-colors font-mono"
                    >
                      kick
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {/* Danger Zone — owner only */}
      {isOwner && (
        <div className="mt-8 border border-[var(--text-error)]/30 rounded-lg p-4">
          <h4 className="text-xs font-mono text-[var(--text-error)] uppercase tracking-widest mb-3">
            Danger Zone
          </h4>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-primary)]">Delete this server</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                Permanently removes the server and all its channels and messages.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="ml-4 px-3 py-1.5 text-xs font-mono rounded
                         border border-[var(--text-error)]/50 text-[var(--text-error)]
                         hover:bg-[var(--text-error)]/10 transition-colors flex-shrink-0"
            >
              Delete server
            </button>
          </div>
        </div>
      )}

      {/* Confirmation dialogs */}
      {confirmKick && (
        <ConfirmDialog
          title="Remove Member"
          message={`Remove ${confirmKick.display_name || confirmKick.username} from ${server?.name}?`}
          confirmLabel="Remove"
          danger
          working={working}
          onConfirm={handleKick}
          onCancel={() => setConfirmKick(null)}
        />
      )}
      {confirmTransfer && (
        <ConfirmDialog
          title="Transfer Ownership"
          message={`Transfer ownership of ${server?.name} to ${confirmTransfer.display_name || confirmTransfer.username}? You will become an admin.`}
          confirmLabel="Transfer"
          working={working}
          onConfirm={handleTransfer}
          onCancel={() => setConfirmTransfer(null)}
        />
      )}
      {confirmDelete && (
        <ConfirmDialog
          title="Delete Server"
          message={`Are you sure you want to delete "${server?.name}"? This will permanently remove all channels and messages. This cannot be undone.`}
          confirmLabel="Delete Server"
          danger
          working={working}
          onConfirm={handleDeleteServer}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  )
}

function ConfirmDialog({ title, message, confirmLabel, danger = false, working, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60]">
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-6
                      max-w-sm w-full mx-4 shadow-xl">
        <h4 className="text-sm font-bold text-[var(--text-primary)] mb-2">{title}</h4>
        <p className="text-sm text-[var(--text-lt)] mb-5">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-xs font-mono rounded border border-[var(--border)]
                       text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={working}
            className={`px-3 py-1.5 text-xs font-mono rounded border disabled:opacity-40
                        disabled:cursor-not-allowed transition-colors
                        ${danger
                          ? 'bg-[var(--text-error)]/20 border-[var(--text-error)]/50 text-[var(--text-error)] hover:bg-[var(--text-error)]/30'
                          : 'bg-[var(--accent-teal)]/20 border-[var(--accent-teal)]/50 text-[var(--accent-teal)] hover:bg-[var(--accent-teal)]/30'
                        }`}
          >
            {working ? '…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function ChannelsTab({ serverId }) {
  const channels = useChatStore((s) => s.channels)
  const deleteChannel = useChatStore((s) => s.deleteChannel)
  const [confirmId, setConfirmId] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const confirmChannel = channels.find((c) => c.id === confirmId)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteChannel(serverId, confirmId)
      setConfirmId(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="server-settings-modal__section">
      <h3>Channels</h3>
      <p className="server-settings-modal__description">
        Delete channels you no longer need. This action cannot be undone.
      </p>
      <ul className="mt-4 flex flex-col gap-1">
        {channels.map((ch) => (
          <li key={ch.id} className="flex items-center justify-between px-3 py-2 rounded
                                     bg-[var(--bg-hover)] font-mono text-sm">
            <span className="text-[var(--text-muted)]">#</span>
            <span className="flex-1 ml-1 text-[var(--text-primary)]">{ch.name}</span>
            <button
              type="button"
              title={`Delete #${ch.name}`}
              onClick={() => setConfirmId(ch.id)}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-error)]
                         transition-colors px-1 font-mono"
            >
              delete
            </button>
          </li>
        ))}
      </ul>

      {confirmId && (
        <ConfirmDialog
          title="Delete Channel"
          message={`Are you sure you want to delete #${confirmChannel?.name}? All messages will be permanently removed.`}
          confirmLabel="Delete"
          danger
          working={deleting}
          onConfirm={handleDelete}
          onCancel={() => setConfirmId(null)}
        />
      )}
    </div>
  )
}

export function ServerSettingsModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('appearance')
  const [nicknameOpen, setNicknameOpen] = useState(false)
  const activeServerId = useServerStore((s) => s.activeServerId)
  const servers = useServerStore((s) => s.servers)
  const server = servers.find((s) => s.id === activeServerId)

  const tabs = [
    { id: 'appearance', label: 'Appearance' },
    { id: 'invite', label: 'Invite People' },
    { id: 'channels', label: 'Channels' },
    { id: 'members', label: 'Members' },
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
          <button
            className="server-settings-modal__tab"
            onClick={() => setNicknameOpen(true)}
            type="button"
          >
            My Nickname
          </button>
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
          {activeTab === 'channels' && <ChannelsTab serverId={activeServerId} />}
          {activeTab === 'members' && <MembersTab server={server} onClose={onClose} />}
        </div>
      </div>

      {nicknameOpen && (
        <SetNicknameModal
          serverId={activeServerId}
          current={null}
          onClose={() => setNicknameOpen(false)}
        />
      )}
    </div>
  )
}
