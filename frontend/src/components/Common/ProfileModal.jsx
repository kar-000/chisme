import { useEffect, useState } from 'react'
import Modal from './Modal'
import StatusIndicator from './StatusIndicator'
import useAuthStore from '../../store/authStore'
import { getUser, updateMe } from '../../services/users'

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

/**
 * Shows a user profile.  When userId === current user's id, shows edit controls.
 */
export default function ProfileModal({ userId, onClose }) {
  const { user: me, setUser } = useAuthStore()
  const isOwn = userId === me?.id

  const [profile, setProfile] = useState(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ display_name: '', bio: '', status: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

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
  }, [userId])

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
          ? editing
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
          : null
      }
    >
      {/* Header row */}
      <div className="flex items-center gap-4 mb-5">
        <Avatar username={profile.username} avatarUrl={profile.avatar_url} size={56} />
        <div className="min-w-0">
          <p className="text-base font-semibold text-[var(--text-primary)] glow-teal truncate">
            {displayedName}
          </p>
          {profile.display_name && (
            <p className="text-xs text-[var(--text-muted)] font-mono">@{profile.username}</p>
          )}
          <div className="flex items-center gap-1.5 mt-1">
            <StatusIndicator status={profile.status} size="sm" />
            <span className="text-xs text-[var(--text-muted)] font-mono">{profile.status}</span>
          </div>
        </div>
      </div>

      {error && <p className="text-[var(--text-error)] text-xs mb-3">{error}</p>}

      {editing ? (
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
      )}
    </Modal>
  )
}
