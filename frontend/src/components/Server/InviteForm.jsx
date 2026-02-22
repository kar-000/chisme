import { useState } from 'react'
import { createInvite } from '../../services/servers'

/**
 * Inline invite link generator. Used inside InviteModal and ServerSettingsModal.
 * serverId and serverName are passed as props so it works in both contexts.
 */
export function InviteForm({ serverId, serverName }) {
  const [maxUses, setMaxUses] = useState('')
  const [expiryHours, setExpiryHours] = useState('')
  const [inviteUrl, setInviteUrl] = useState(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setCopied(false)
    try {
      const payload = {}
      if (maxUses !== '') payload.max_uses = parseInt(maxUses, 10)
      if (expiryHours !== '') payload.expires_in_hours = parseInt(expiryHours, 10)
      const { data } = await createInvite(serverId, payload)
      setInviteUrl(`${window.location.origin}/invite/${data.code}`)
    } catch (e) {
      setError(e.response?.data?.detail ?? 'Failed to generate invite link.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl)
    } catch {
      const input = document.createElement('input')
      input.value = inviteUrl
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const handleReset = () => {
    setInviteUrl(null)
    setCopied(false)
    setMaxUses('')
    setExpiryHours('')
  }

  if (inviteUrl) {
    return (
      <div className="invite-form__result">
        <p className="invite-form__hint">
          Share this link. Anyone with it can join {serverName}.
          {maxUses && ` · ${maxUses} use${maxUses === '1' ? '' : 's'}`}
          {expiryHours && ` · Expires in ${expiryHours}h`}
        </p>
        <div className="invite-form__link-row">
          <input
            className="invite-form__link-input"
            value={inviteUrl}
            readOnly
            onFocus={(e) => e.target.select()}
          />
          <button
            className={`invite-form__copy-btn${copied ? ' invite-form__copy-btn--copied' : ''}`}
            onClick={handleCopy}
            type="button"
          >
            {copied ? '✓ Copied!' : 'Copy'}
          </button>
        </div>
        <button className="invite-form__regenerate" onClick={handleReset} type="button">
          Generate another link with different settings
        </button>
      </div>
    )
  }

  return (
    <div className="invite-form__options">
      <p className="invite-form__hint">
        Configure the invite link before generating. Leave fields blank for no limit.
      </p>
      <div className="invite-form__selects">
        <div className="invite-form__select-group">
          <label>Max uses</label>
          <select
            value={maxUses}
            onChange={(e) => setMaxUses(e.target.value)}
            className="invite-select"
          >
            <option value="">Unlimited</option>
            <option value="1">1 use</option>
            <option value="5">5 uses</option>
            <option value="10">10 uses</option>
            <option value="25">25 uses</option>
            <option value="50">50 uses</option>
            <option value="100">100 uses</option>
          </select>
        </div>
        <div className="invite-form__select-group">
          <label>Expires after</label>
          <select
            value={expiryHours}
            onChange={(e) => setExpiryHours(e.target.value)}
            className="invite-select"
          >
            <option value="">Never</option>
            <option value="1">1 hour</option>
            <option value="6">6 hours</option>
            <option value="12">12 hours</option>
            <option value="24">24 hours</option>
            <option value="72">3 days</option>
            <option value="168">7 days</option>
          </select>
        </div>
      </div>
      {error && <p className="invite-form__error">{error}</p>}
      <button
        className="btn-primary invite-form__generate"
        onClick={handleGenerate}
        disabled={loading}
        type="button"
      >
        {loading ? 'Generating…' : 'Generate Invite Link'}
      </button>
    </div>
  )
}
