import { useState } from 'react'
import { setNickname, clearNickname } from '../../services/users'

/**
 * SetNicknameModal — lets the current user set or clear their per-server nickname.
 *
 * Props:
 *   serverId  — the server to set the nickname in
 *   current   — the user's current nickname (or null/undefined)
 *   onClose   — called when the modal should close
 */
export default function SetNicknameModal({ serverId, current, onClose }) {
  const [value, setValue] = useState(current ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    const trimmed = value.trim()
    if (!trimmed) {
      await handleClear()
      return
    }
    if (trimmed.length > 32) {
      setError('Nickname must be 32 characters or fewer')
      return
    }
    setSaving(true)
    setError('')
    try {
      await setNickname(serverId, trimmed)
      onClose()
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to set nickname')
    } finally {
      setSaving(false)
    }
  }

  const handleClear = async () => {
    setSaving(true)
    setError('')
    try {
      await clearNickname(serverId)
      onClose()
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to clear nickname')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-6
                      max-w-sm w-full shadow-xl">
        <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1">Set Server Nickname</h3>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          Only visible in this server. Leave blank to clear.
        </p>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave() }}
          maxLength={32}
          placeholder="Nickname (max 32 chars)"
          autoFocus
          className="w-full px-3 py-2 text-sm font-mono rounded border border-[var(--border)]
                     bg-[var(--bg-primary)] text-[var(--text-primary)] outline-none
                     focus:border-[var(--accent-teal)] mb-1"
        />
        <div className="text-right text-xs text-[var(--text-muted)] mb-3">
          {value.length}/32
        </div>
        {error && (
          <p className="text-xs font-mono text-[var(--text-error)] mb-3">&gt; {error}</p>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-3 py-1.5 text-xs font-mono rounded border border-[var(--border)]
                       text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors
                       disabled:opacity-40"
          >
            Cancel
          </button>
          {current && (
            <button
              type="button"
              onClick={handleClear}
              disabled={saving}
              className="px-3 py-1.5 text-xs font-mono rounded border border-[var(--text-error)]/50
                         text-[var(--text-error)] hover:bg-[var(--text-error)]/10 transition-colors
                         disabled:opacity-40"
            >
              {saving ? '…' : 'Clear'}
            </button>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 text-xs font-mono rounded border border-[var(--accent-teal)]/50
                       text-[var(--accent-teal)] hover:bg-[var(--accent-teal)]/10 transition-colors
                       disabled:opacity-40"
          >
            {saving ? '…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
