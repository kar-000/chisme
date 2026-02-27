/**
 * VoiceUser — a small chip showing a user currently in voice.
 * Shows username + mute indicator. Glows teal when the user is speaking.
 * Shows a colored health dot for remote peers (teal=connected, orange=connecting, pink=failed).
 * Shows a pulsing ↻ badge when the user is temporarily reconnecting.
 */
import useChatStore from '../../store/chatStore'

export default function VoiceUser({ user, isLocalUser }) {
  const isSpeaking = !user.muted && user.speaking
  const connState = useChatStore((s) => s.peerConnectionStates[user.user_id])

  const dotColor = isLocalUser ? null
    : connState === 'connected'    ? 'var(--crt-teal)'
    : connState === 'failed'       ? 'var(--crt-pink)'
    : connState != null            ? 'var(--crt-orange)'
    : null

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono
                 bg-[var(--crt-dark)] border text-[var(--crt-teal)] transition-shadow
                 ${isSpeaking
                   ? 'border-[var(--crt-teal)] shadow-[0_0_8px_rgba(0,206,209,0.6)]'
                   : 'border-[var(--crt-teal)]/40'}`}
      title={user.display_name || user.username}
    >
      {dotColor && (
        <span style={{ color: dotColor, fontSize: '0.5rem' }} title={connState}>●</span>
      )}
      {user.muted ? (
        <span className="text-[var(--crt-orange)]" aria-label="muted">🔇</span>
      ) : (
        <span className="text-[var(--crt-teal)]" aria-label="speaking">🎙</span>
      )}
      {user.reconnecting && (
        <span className="text-[var(--crt-orange)] animate-pulse" title="Reconnecting…">↻</span>
      )}
      {user.display_name || user.username}
    </span>
  )
}
