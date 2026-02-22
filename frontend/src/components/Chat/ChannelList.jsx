import { useState } from 'react'
import useChatStore from '../../store/chatStore'
import useDMStore from '../../store/dmStore'
import useServerStore from '../../store/serverStore'
import { useInviteModal } from '../../hooks/useInviteModal'
import { ServerSettingsModal } from '../Server/ServerSettingsModal'
import Modal from '../Common/Modal'
import Input from '../Common/Input'
import Button from '../Common/Button'

export default function ChannelList({ onNavigate }) {
  const { channels, activeChannelId, unreadCounts, selectChannel, createChannel } = useChatStore()
  const closeDM = useDMStore((s) => s.closeDM)
  const activeServerId = useServerStore((s) => s.activeServerId)
  const servers = useServerStore((s) => s.servers)
  const server = servers.find((s) => s.id === activeServerId)
  const canInvite =
    server?.current_user_role === 'owner' || server?.current_user_role === 'admin'

  const invite = useInviteModal()
  const [showSettings, setShowSettings] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      await createChannel(activeServerId, name.toLowerCase(), desc)
      setShowModal(false)
      setName('')
      setDesc('')
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to create channel')
    } finally {
      setCreating(false)
    }
  }

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Server name header with invite / settings buttons */}
        <div className="sidebar-server-header">
          <span className="sidebar-server-name">{server?.name ?? '…'}</span>
          {canInvite && (
            <div className="flex items-center gap-1">
              <button
                className="sidebar-invite-btn"
                onClick={invite.open}
                title="Invite People"
                type="button"
              >
                +👤
              </button>
              <button
                className="sidebar-settings-btn"
                onClick={() => setShowSettings(true)}
                title="Server Settings"
                type="button"
              >
                ⚙
              </button>
            </div>
          )}
        </div>

        {/* Channel list header row */}
        <div className="px-3 py-2 flex items-center justify-between">
          <span className="text-xs text-[var(--text-muted)] uppercase tracking-widest">Channels</span>
          {canInvite && (
            <button
              onClick={() => setShowModal(true)}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg leading-none transition-colors"
              title="New channel"
              type="button"
            >
              +
            </button>
          )}
        </div>

        <ul className="flex-1 overflow-y-auto">
          {channels.map((ch) => {
            const unread = unreadCounts?.[ch.id] ?? 0
            const isActive = activeChannelId === ch.id
            return (
              <li key={ch.id}>
                <button
                  onClick={() => { closeDM(); selectChannel(activeServerId, ch.id); onNavigate?.() }}
                  className={`
                    w-full text-left px-4 py-2 text-sm flex items-center gap-1
                    border-l-2 transition-all duration-150
                    ${isActive
                      ? 'border-[var(--accent-teal)] bg-[var(--bg-active)] text-[var(--text-primary)] glow-teal'
                      : unread > 0
                        ? 'border-[var(--crt-orange)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
                        : 'border-transparent text-[var(--text-lt)] hover:bg-[var(--bg-hover)] hover:border-[var(--accent-teal)]'
                    }
                  `}
                >
                  <span className="text-[var(--text-muted)]">#</span>
                  <span className="truncate flex-1">{ch.name}</span>
                  {ch.voice_count > 0 && (
                    <span className="text-xs font-mono text-[var(--accent-teal)] shrink-0 flex items-center gap-0.5">
                      🎤{ch.voice_count}
                    </span>
                  )}
                  {!isActive && unread > 0 && (
                    <span className="ml-auto text-xs font-bold px-1.5 py-0.5 rounded-full
                                     bg-[var(--crt-orange)] text-[var(--crt-dark)] shrink-0">
                      {unread > 99 ? '99+' : unread}
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      {showSettings && <ServerSettingsModal onClose={() => setShowSettings(false)} />}

      {showModal && (
        <Modal
          title="New Channel"
          onClose={() => setShowModal(false)}
          footer={
            <>
              <Button variant="ghost" type="button" onClick={() => setShowModal(false)}>Cancel</Button>
              <Button type="submit" form="new-channel-form" disabled={creating}>
                {creating ? 'Creating...' : 'Create'}
              </Button>
            </>
          }
        >
          <form id="new-channel-form" onSubmit={handleCreate} className="flex flex-col gap-4">
            {error && <p className="text-xs text-[var(--text-error)]">&gt; {error}</p>}
            <Input
              label="Channel name (lowercase, a-z0-9-)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-channel"
              required
              autoFocus
            />
            <Input
              label="Description (optional)"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="What's this channel about?"
            />
          </form>
        </Modal>
      )}
    </>
  )
}
