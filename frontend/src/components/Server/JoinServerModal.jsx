import { useState } from 'react'
import { previewInvite, redeemInvite } from '../../services/servers'
import useServerStore from '../../store/serverStore'

export function JoinServerModal({ initialCode = '', onClose }) {
  const [code, setCode] = useState(initialCode)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const fetchServers = useServerStore((s) => s.fetchServers)
  const setActiveServer = useServerStore((s) => s.setActiveServer)

  const handlePreview = async () => {
    if (!code.trim()) return
    setError(null)
    try {
      const { data } = await previewInvite(code.trim())
      setPreview(data)
    } catch {
      setPreview(null)
      setError('Invite not found or expired.')
    }
  }

  const handleJoin = async () => {
    if (!code.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const { data } = await redeemInvite(code.trim())
      await fetchServers()
      setActiveServer(data.server_id)
      onClose()
    } catch (e) {
      setError(e.response?.data?.detail ?? 'Failed to join server.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Join a Server</h2>
          <button className="modal-close" onClick={onClose} type="button">✕</button>
        </div>
        <div className="modal-body">
          <label className="modal-label">Invite Code</label>
          <div className="modal-input-row">
            <input
              className="modal-input"
              value={code}
              onChange={(e) => { setCode(e.target.value); setPreview(null) }}
              placeholder="abc123def456"
            />
            <button className="btn-secondary" onClick={handlePreview} type="button">
              Preview
            </button>
          </div>
          {preview && (
            <div className="invite-preview">
              <strong className="invite-preview__name">{preview.server_name}</strong>
              {preview.server_description && (
                <p className="invite-preview__desc">{preview.server_description}</p>
              )}
              <span className="invite-preview__count">{preview.member_count} members</span>
            </div>
          )}
          {error && <p className="modal-error">{error}</p>}
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} type="button">Cancel</button>
          <button
            className="btn-primary"
            onClick={handleJoin}
            disabled={!preview || submitting}
            type="button"
          >
            {submitting ? 'Joining…' : 'Join Server'}
          </button>
        </div>
      </div>
    </div>
  )
}
