import { useState } from 'react'
import { castVote, removeVote } from '../../services/polls'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'

function formatRelative(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  const now = new Date()
  const diff = d - now
  if (diff < 0) return 'closed'
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(diff / 3600000)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(diff / 86400000)
  return `${days}d`
}

export default function PollMessage({ poll, messageId }) {
  const { user } = useAuthStore()
  const updatePollInMessage = useChatStore((s) => s.updatePollInMessage)
  const [voting, setVoting] = useState(false)

  if (!poll) return null

  const isClosed =
    poll.closes_at && new Date(poll.closes_at) < new Date()
  const userVoted = new Set(poll.user_voted_option_ids ?? [])
  const closesIn = poll.closes_at ? formatRelative(poll.closes_at) : null

  const handleVote = async (optionId) => {
    if (isClosed || voting) return
    setVoting(true)
    try {
      const alreadyVoted = userVoted.has(optionId)
      let newVotedIds

      if (alreadyVoted && poll.multi_choice) {
        // In multi-choice, clicking a voted option removes just that vote
        // (we remove all then re-add remaining — simplest approach)
        newVotedIds = [...userVoted].filter((id) => id !== optionId)
      } else if (alreadyVoted && !poll.multi_choice) {
        // Single choice: clicking same option = un-vote
        await removeVote(poll.id)
        updatePollInMessage(messageId, { user_voted_option_ids: [] })
        return
      } else {
        // New vote
        newVotedIds = poll.multi_choice ? [...userVoted, optionId] : [optionId]
      }

      if (newVotedIds.length === 0) {
        await removeVote(poll.id)
        updatePollInMessage(messageId, { user_voted_option_ids: [] })
      } else {
        const { data } = await castVote(poll.id, newVotedIds)
        updatePollInMessage(messageId, {
          options: data.options,
          total_votes: data.total_votes,
          user_voted_option_ids: data.user_voted_option_ids,
        })
      }
    } catch {
      // silently ignore
    } finally {
      setVoting(false)
    }
  }

  return (
    <div className={`poll-card${isClosed ? ' poll-closed' : ''}`}>
      <div className="poll-question">{poll.question}</div>
      {isClosed && <div className="poll-closed-banner">Poll closed</div>}

      <div className="poll-options">
        {poll.options.map((option) => {
          const voted = userVoted.has(option.id)
          const pct = option.percentage ?? 0
          return (
            <div
              key={option.id}
              className={`poll-option${voted ? ' voted' : ''}${isClosed ? ' poll-option-locked' : ''}`}
              onClick={() => !isClosed && handleVote(option.id)}
              role={isClosed ? undefined : 'button'}
              tabIndex={isClosed ? undefined : 0}
              onKeyDown={(e) => e.key === 'Enter' && !isClosed && handleVote(option.id)}
            >
              <span className="poll-option-text">{option.text}</span>
              <div className="poll-bar-track">
                <div
                  className="poll-bar-fill"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="poll-pct">{pct}%</span>
              {voted && <span className="poll-voted-mark">✓</span>}
            </div>
          )
        })}
      </div>

      <div className="poll-meta">
        {poll.total_votes} vote{poll.total_votes !== 1 ? 's' : ''}
        {closesIn && closesIn !== 'closed' && (
          <span> · Closes in {closesIn}</span>
        )}
        {poll.multi_choice && <span> · Multiple choice</span>}
        {isClosed && <span> · Final results</span>}
      </div>
    </div>
  )
}
