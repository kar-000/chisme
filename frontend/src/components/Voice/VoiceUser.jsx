/**
 * VoiceUser — a small chip showing a user currently in voice.
 * Shows username + mute indicator. Glows teal when the user is speaking.
 */
export default function VoiceUser({ user }) {
  const isSpeaking = !user.muted && user.speaking
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono
                 bg-[var(--crt-dark)] border text-[var(--crt-teal)] transition-shadow
                 ${isSpeaking
                   ? 'border-[var(--crt-teal)] shadow-[0_0_8px_rgba(0,206,209,0.6)]'
                   : 'border-[var(--crt-teal)]/40'}`}
      title={user.display_name || user.username}
    >
      {user.muted ? (
        <span className="text-[var(--crt-orange)]" aria-label="muted">🔇</span>
      ) : (
        <span className="text-[var(--crt-teal)]" aria-label="speaking">🎙</span>
      )}
      {user.display_name || user.username}
    </span>
  )
}
