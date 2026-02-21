/**
 * VoiceUser — a small chip showing a user currently in voice.
 * Shows username + mute indicator.
 */
export default function VoiceUser({ user }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono
                 bg-[var(--crt-dark)] border border-[var(--crt-teal)] text-[var(--crt-teal)]"
      title={user.username}
    >
      {user.muted ? (
        <span className="text-[var(--crt-orange)]" aria-label="muted">🔇</span>
      ) : (
        <span className="text-[var(--crt-teal)]" aria-label="speaking">🎙</span>
      )}
      {user.username}
    </span>
  )
}
