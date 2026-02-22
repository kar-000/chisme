import { useState } from 'react'
import { createServer } from '../../services/servers'
import useServerStore from '../../store/serverStore'

export function CreateServerModal({ onClose }) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const addServer = useServerStore((s) => s.addServer)
  const setActiveServer = useServerStore((s) => s.setActiveServer)

  const handleSubmit = async () => {
    if (!name.trim() || !slug.trim()) {
      setError('Name and slug are required.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const { data } = await createServer({ name: name.trim(), slug: slug.trim() })
      addServer(data)
      setActiveServer(data.id)
      onClose()
    } catch (e) {
      setError(e.response?.data?.detail ?? 'Failed to create server.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create a Server</h2>
          <button className="modal-close" onClick={onClose} type="button">✕</button>
        </div>
        <div className="modal-body">
          <label className="modal-label">Server Name</label>
          <input
            className="modal-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Community"
            maxLength={100}
          />
          <label className="modal-label">
            Slug <span className="modal-hint">(URL identifier, e.g. my-community)</span>
          </label>
          <input
            className="modal-input"
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase())}
            placeholder="my-community"
            maxLength={100}
          />
          {error && <p className="modal-error">{error}</p>}
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} type="button">Cancel</button>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={submitting}
            type="button"
          >
            {submitting ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
