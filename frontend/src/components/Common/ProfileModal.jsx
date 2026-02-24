import { useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import StatusIndicator from './StatusIndicator'
import useAuthStore from '../../store/authStore'
import useDMStore from '../../store/dmStore'
import useChatStore from '../../store/chatStore'
import { getUser, updateMe, uploadAvatar, getQuietHours, updateQuietHours } from '../../services/users'
import { isInQuietHours } from '../../utils/quietHours'

function Avatar({ username, avatarUrl, size = 56 }) {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={username}
        className="rounded-full object-cover border-2 border-[var(--border-glow)]"
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <div
      className="rounded-full flex items-center justify-center font-bold
                 bg-gradient-to-br from-crt-teal to-crt-teal-lt text-crt-bg shadow-glow-sm"
      style={{ width: size, height: size, fontSize: size * 0.32 }}
    >
      {username?.slice(0, 2).toUpperCase()}
    </div>
  )
}

const TIMEZONES = typeof Intl.supportedValuesOf === 'function'
  ? Intl.supportedValuesOf('timeZone')
  : ['UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo']

function QuietHoursPanel({ qh, saving, error, onChange }) {
  const enabled = qh?.enabled ?? false
  const start = qh?.start ?? '23:00'
  const end = qh?.end ?? '08:00'
  const tz = qh?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone
  const override = qh?.dnd_override ?? null

  return (
    <div className="quiet-hours-panel">
      {/* Enable toggle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-[var(--text-primary)] font-mono">Quiet Hours</p>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">Suppress notifications during a scheduled window</p>
        </div>
        <button
          type="button"
          onClick={() => onChange({ enabled: !enabled, start, end, timezone: tz, dnd_override: override })}
          disabled={saving}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors
            ${enabled ? 'bg-[var(--accent-teal)]' : 'bg-[var(--border)]'} disabled:opacity-50`}
        >
          <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform
            ${enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
        </button>
      </div>

      {/* Time range */}
      <div className={`quiet-hours-times transition-opacity ${enabled ? '' : 'opacity-40 pointer-events-none'}`}>
        <span className="text-xs font-mono text-[var(--text-muted)]">From</span>
        <input
          type="time"
          value={start}
          onChange={(e) => onChange({ enabled, start: e.target.value, end, timezone: tz, dnd_override: override })}
          disabled={saving}
        />
        <span className="text-xs font-mono text-[var(--text-muted)]">to</span>
        <input
          type="time"
          value={end}
          onChange={(e) => onChange({ enabled, start, end: e.target.value, timezone: tz, dnd_override: override })}
          disabled={saving}
        />
      </div>

      {/* Timezone */}
      <div className={`transition-opacity ${enabled ? '' : 'opacity-40 pointer-events-none'}`}>
        <label className="block text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mb-1">
          Timezone
        </label>
        <select
          value={tz}
          onChange={(e) => onChange({ enabled, start, end, timezone: e.target.value, dnd_override: override })}
          disabled={saving}
          className="w-full bg-black/40 border border-[var(--border)] rounded px-2 py-1
                     text-xs font-mono text-[var(--text-primary)] focus:outline-none
                     focus:border-[var(--border-glow)]"
        >
          {TIMEZONES.map((z) => <option key={z} value={z}>{z}</option>)}
        </select>
      </div>

      {/* Manual DND override */}
      <div>
        <label className="block text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mb-1.5">
          Manual Override
        </label>
        <div className="dnd-override-group">
          {[['auto', null], ['force on', 'on'], ['force off', 'off']].map(([label, val]) => (
            <button
              key={label}
              type="button"
              disabled={saving}
              onClick={() => onChange({ enabled, start, end, timezone: tz, dnd_override: val })}
              className={override === val ? 'active' : ''}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-[var(--text-muted)] font-mono mt-1">
          Override takes priority over the schedule.
        </p>
      </div>

      {saving && <p className="text-xs font-mono text-[var(--text-muted)]">Saving…</p>}
      {error && <p className="text-xs font-mono text-[var(--text-error)]">{error}</p>}
    </div>
  )
}

/**
 * Shows a user profile.  When userId === current user's id, shows edit controls.
 */
export default function ProfileModal({ userId, onClose }) {
  const { user: me, setUser, quietHours: storedQH, setQuietHours } = useAuthStore()
  const isOwn = userId === me?.id
  const openDM = useDMStore((s) => s.openDM)
  const clearActiveChannel = useChatStore((s) => s.clearActiveChannel)

  const [profile, setProfile] = useState(null)
  const [activeTab, setActiveTab] = useState('profile')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ display_name: '', bio: '', status: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const avatarInputRef = useRef(null)

  // Quiet hours state (own profile only)
  const [qh, setQh] = useState(null)
  const [qhSaving, setQhSaving] = useState(false)
  const [qhError, setQhError] = useState(null)

  useEffect(() => {
    getUser(userId)
      .then((res) => {
        setProfile(res.data)
        setForm({
          display_name: res.data.display_name ?? '',
          bio: res.data.bio ?? '',
          status: res.data.status ?? 'online',
        })
      })
      .catch(() => setError('Could not load profile.'))
    if (isOwn) {
      const initial = storedQH ?? null
      if (initial) setQh(initial)
      getQuietHours()
        .then((r) => {
          setQh(r.data)
          setQuietHours(r.data)
        })
        .catch(() => {})
    }
  }, [userId]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleMessageUser = async () => {
    clearActiveChannel()
    await openDM(userId)
    onClose()
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload = {
        display_name: form.display_name.trim() || null,
        bio: form.bio.trim() || null,
        status: form.status,
      }
      const res = await updateMe(payload)
      setProfile(res.data)
      setUser(res.data)
      setEditing(false)
    } catch {
      setError('Failed to save changes.')
    } finally {
      setSaving(false)
    }
  }

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarUploading(true)
    setError(null)
    try {
      const res = await uploadAvatar(file)
      setProfile(res.data)
      setUser(res.data)
    } catch {
      setError('Avatar upload failed.')
    } finally {
      setAvatarUploading(false)
      e.target.value = ''
    }
  }

  if (!profile && !error) {
    return (
      <Modal title="Profile" onClose={onClose}>
        <p className="text-[var(--text-muted)] text-sm font-mono text-center py-4">Loading…</p>
      </Modal>
    )
  }

  if (error && !profile) {
    return (
      <Modal title="Profile" onClose={onClose}>
        <p className="text-[var(--text-error)] text-sm font-mono text-center py-4">{error}</p>
      </Modal>
    )
  }

  const displayedName = profile.display_name || profile.username

  return (
    <Modal
      title={isOwn ? 'Your Profile' : 'User Profile'}
      onClose={onClose}
      footer={
        isOwn
          ? activeTab === 'notifications'
            ? null
            : editing
              ? <>
                  <button
                    onClick={() => setEditing(false)}
                    className="px-4 py-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-4 py-1.5 text-sm bg-[var(--crt-teal)] text-[var(--crt-dark)]
                               font-bold rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </>
              : <button
                  onClick={() => setEditing(true)}
                  className="px-4 py-1.5 text-sm border border-[var(--border-glow)]
                             text-[var(--text-primary)] rounded hover:bg-white/5 transition-colors"
                >
                  Edit Profile
                </button>
          : <button
              onClick={handleMessageUser}
              className="px-4 py-1.5 text-sm bg-[var(--crt-teal)] text-[var(--crt-dark)]
                         font-bold rounded hover:opacity-90 transition-opacity"
            >
              Message
            </button>
      }
    >
      {/* Header row */}
      <div className="flex items-center gap-4 mb-5">
        {isOwn ? (
          <button
            onClick={() => avatarInputRef.current?.click()}
            disabled={avatarUploading}
            className="relative group shrink-0 rounded-full focus:outline-none focus:ring-2 focus:ring-[var(--border-glow)]"
            title="Change avatar"
          >
            <Avatar username={profile.username} avatarUrl={profile.avatar_url} size={56} />
            <span className="absolute inset-0 flex items-center justify-center rounded-full
                             bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity text-lg">
              {avatarUploading ? '…' : '📷'}
            </span>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              className="hidden"
              onChange={handleAvatarChange}
            />
          </button>
        ) : (
          <Avatar username={profile.username} avatarUrl={profile.avatar_url} size={56} />
        )}
        <div className="min-w-0">
          <p className="text-base font-semibold text-[var(--text-primary)] glow-teal truncate">
            {displayedName}
          </p>
          {profile.display_name && (
            <p className="text-xs text-[var(--text-muted)] font-mono">@{profile.username}</p>
          )}
          <div className="flex items-center gap-1.5 mt-1">
            <StatusIndicator
              status={profile.status}
              size="sm"
              inQuietHours={isOwn ? isInQuietHours(qh) : false}
            />
            <span className="text-xs text-[var(--text-muted)] font-mono">
              {isOwn && isInQuietHours(qh) ? 'quiet hours' : profile.status}
            </span>
          </div>
        </div>
      </div>

      {/* Tab bar — own profile only */}
      {isOwn && (
        <div className="flex gap-1 mb-4 border-b border-[var(--border)] pb-0">
          {['profile', 'notifications'].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => { setActiveTab(tab); setEditing(false) }}
              className={`px-3 py-1.5 text-xs font-mono rounded-t transition-colors
                ${activeTab === tab
                  ? 'text-[var(--accent-teal)] border-b-2 border-[var(--accent-teal)] -mb-px'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'}`}
            >
              {tab}
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-[var(--text-error)] text-xs mb-3">{error}</p>}

      {/* Profile tab */}
      {activeTab === 'profile' && (editing ? (
        <div className="flex flex-col gap-3">
          <div>
            <label className="block text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mb-1">
              Display Name
            </label>
            <input
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              maxLength={50}
              placeholder={profile.username}
              className="w-full bg-black/40 border border-[var(--border)] rounded px-3 py-1.5
                         text-sm font-mono text-[var(--text-primary)] focus:outline-none
                         focus:border-[var(--border-glow)]"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mb-1">
              Bio
            </label>
            <textarea
              value={form.bio}
              onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
              maxLength={500}
              rows={3}
              placeholder="Tell people a bit about yourself…"
              className="w-full bg-black/40 border border-[var(--border)] rounded px-3 py-1.5
                         text-sm font-mono text-[var(--text-primary)] focus:outline-none
                         focus:border-[var(--border-glow)] resize-none"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mb-1">
              Status
            </label>
            <select
              value={form.status}
              onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
              className="w-full bg-black/40 border border-[var(--border)] rounded px-3 py-1.5
                         text-sm font-mono text-[var(--text-primary)] focus:outline-none
                         focus:border-[var(--border-glow)]"
            >
              <option value="online">online</option>
              <option value="away">away</option>
              <option value="dnd">do not disturb</option>
            </select>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {profile.bio ? (
            <p className="text-sm text-[var(--text-primary)] font-mono leading-relaxed">{profile.bio}</p>
          ) : (
            isOwn && (
              <p className="text-sm text-[var(--text-muted)] font-mono italic">
                No bio yet — click "Edit Profile" to add one.
              </p>
            )
          )}
          <p className="text-[10px] text-[var(--text-muted)] font-mono">
            Member since {new Date(profile.created_at).toLocaleDateString()}
          </p>
        </div>
      ))}

      {/* Notifications tab — quiet hours settings */}
      {activeTab === 'notifications' && isOwn && (
        <QuietHoursPanel
          qh={qh}
          saving={qhSaving}
          error={qhError}
          onChange={async (patch) => {
            setQhSaving(true)
            setQhError(null)
            try {
              const { data } = await updateQuietHours(patch)
              setQh(data)
              setQuietHours(data)
            } catch {
              setQhError('Failed to save notification settings.')
            } finally {
              setQhSaving(false)
            }
          }}
        />
      )}
    </Modal>
  )
}
