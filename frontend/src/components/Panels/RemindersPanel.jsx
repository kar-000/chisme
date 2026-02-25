import { useEffect } from 'react'
import useReminderStore from '../../store/reminderStore'
import useChatStore from '../../store/chatStore'
import useServerStore from '../../store/serverStore'

function formatRemindAt(iso) {
  const d = new Date(iso)
  const now = new Date()
  const diff = d - now

  if (diff < 0) return 'overdue'
  if (diff < 60_000) return 'less than a minute'
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)} min`
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)} hr`
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function ReminderItem({ reminder, onCancel, onGoTo }) {
  const msg = reminder.message
  const preview = msg?.content?.slice(0, 100) || '(attachment)'
  const author = msg?.user?.username ?? 'unknown'
  const overdue = new Date(reminder.remind_at) < new Date()

  return (
    <div className="reminder-item" data-testid="reminder-item">
      <div className={`reminder-time${overdue ? ' reminder-overdue' : ''}`}>
        ⏰ {formatRemindAt(reminder.remind_at)}
      </div>
      <div className="bookmark-context">
        <span>{author}</span>
      </div>
      <div className="bookmark-preview" title={msg?.content}>{preview}</div>
      <div className="bookmark-actions">
        {msg?.channel_id && (
          <button type="button" onClick={() => onGoTo(reminder)}>go to</button>
        )}
        <button
          type="button"
          onClick={() => onCancel(reminder.id)}
          className="hover:border-[var(--text-error)] hover:text-[var(--text-error)]"
        >
          cancel
        </button>
      </div>
    </div>
  )
}

export default function RemindersPanel({ onGoToMessage }) {
  const { reminders, loading, fetchReminders, removeReminder } = useReminderStore()

  useEffect(() => {
    fetchReminders()
  }, [fetchReminders])

  const handleGoTo = (reminder) => {
    const channelId = reminder.message?.channel_id
    if (channelId) {
      const serverId = useServerStore.getState().activeServerId
      useChatStore.getState().selectChannel(serverId, channelId)
      onGoToMessage?.()
    }
  }

  return (
    <>
      {loading && (
        <p className="text-xs font-mono text-[var(--text-muted)] text-center py-6">Loading…</p>
      )}
      {!loading && reminders.length === 0 && (
        <p className="text-xs font-mono text-[var(--text-muted)] text-center py-6">
          No reminders. Hover a message and click ⏰ to set one.
        </p>
      )}
      {reminders.map((r) => (
        <ReminderItem
          key={r.id}
          reminder={r}
          onCancel={removeReminder}
          onGoTo={handleGoTo}
        />
      ))}
    </>
  )
}
