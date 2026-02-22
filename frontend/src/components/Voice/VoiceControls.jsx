/**
 * VoiceControls — voice channel bar shown above MessageInput.
 *
 * Props:
 *   channelId   — active channel id
 *   currentUser — { id, username } from authStore
 *   sendMsg     — sendMsg() from useWebSocket
 */
import useChatStore from '../../store/chatStore'
import { useVoiceChat } from '../../hooks/useVoiceChat'
import VoiceUser from './VoiceUser'

function micErrorLabel(micError) {
  if (!micError) return null
  if (micError === 'no-api') return 'no mic API (use localhost or HTTPS)'
  if (micError === 'NotFoundError' || micError === 'DevicesNotFoundError') return 'no mic found'
  if (micError === 'NotAllowedError' || micError === 'PermissionDeniedError') return 'mic blocked'
  return 'mic unavailable'
}

export default function VoiceControls({ currentUser, sendMsg, connected }) {
  const voiceUsers = useChatStore((s) => s.voiceUsers)
  const { inVoice, muted, micError, joinVoice, leaveVoice, toggleMute } = useVoiceChat(
    currentUser,
    sendMsg,
  )

  const participants = Object.values(voiceUsers)
  const micLabel = micErrorLabel(micError)

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 border-t border-[var(--border)]
                 bg-[var(--bg-secondary)] text-xs font-mono flex-wrap"
    >
      {/* Participant chips */}
      {participants.length > 0 ? (
        <div className="flex items-center gap-1 flex-wrap flex-1">
          <span className="text-[var(--text-muted)] mr-1">Voice:</span>
          {participants.map((u) => (
            <VoiceUser key={u.user_id} user={u} />
          ))}
        </div>
      ) : (
        <span className="text-[var(--text-muted)] flex-1">Voice channel — empty</span>
      )}

      {/* Mic warning (listen-only) */}
      {inVoice && micLabel && (
        <span className="text-[var(--crt-orange)]" title="Joined listen-only">
          ⚠ {micLabel}
        </span>
      )}

      {/* Controls */}
      <div className="flex items-center gap-1 ml-auto shrink-0">
        {inVoice && !micError && (
          <button
            onClick={toggleMute}
            title={muted ? 'Unmute' : 'Mute'}
            className="px-2 py-0.5 rounded border border-[var(--crt-orange)] text-[var(--crt-orange)]
                       hover:bg-[var(--crt-orange)] hover:text-[var(--crt-dark)] transition-colors"
          >
            {muted ? '🔇 Unmute' : '🎙 Mute'}
          </button>
        )}
        <button
          onClick={inVoice ? leaveVoice : joinVoice}
          disabled={!inVoice && !connected}
          title={inVoice ? 'Leave voice' : connected ? 'Join voice' : 'Connecting…'}
          className={`px-2 py-0.5 rounded border transition-colors
            ${inVoice
              ? 'border-[var(--crt-pink)] text-[var(--crt-pink)] hover:bg-[var(--crt-pink)] hover:text-[var(--crt-dark)]'
              : connected
                ? 'border-[var(--crt-teal)] text-[var(--crt-teal)] hover:bg-[var(--crt-teal)] hover:text-[var(--crt-dark)]'
                : 'border-[var(--text-muted)] text-[var(--text-muted)] cursor-not-allowed opacity-50'
            }`}
        >
          {inVoice ? '📵 Leave' : '📞 Join'}
        </button>
      </div>
    </div>
  )
}
