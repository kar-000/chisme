import { useState, useEffect, useRef, useCallback } from 'react'
import useChannelNotesStore from '../../store/channelNotesStore'
import { MessageContent } from './MessageContent'
import NotesHistoryModal from '../Modals/NotesHistoryModal'

const AUTOSAVE_DELAY = 1200 // ms after last keystroke

export default function ChannelNotes({ channelId, open }) {
  const { cache, fetchNotes, saveNotes } = useChannelNotesStore()
  const notes = cache[channelId]

  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [baseVersion, setBaseVersion] = useState(1)
  const [saveStatus, setSaveStatus] = useState('') // '' | 'saving' | 'saved' | 'conflict'
  const [conflictData, setConflictData] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const autosaveTimer = useRef(null)
  const statusTimer = useRef(null)

  // Fetch notes when panel opens
  useEffect(() => {
    if (open && channelId) {
      fetchNotes(channelId)
    }
  }, [open, channelId, fetchNotes])

  // Sync draft when notes load or change from WS
  useEffect(() => {
    if (!editing) {
      setDraft(notes?.content ?? '')
      setBaseVersion(notes?.version ?? 1)
    }
  }, [notes, editing])

  const doSave = useCallback(async (content, version) => {
    setSaveStatus('saving')
    setConflictData(null)
    try {
      const saved = await saveNotes(channelId, content, version)
      setBaseVersion(saved.version)
      setSaveStatus('saved')
      clearTimeout(statusTimer.current)
      statusTimer.current = setTimeout(() => setSaveStatus(''), 2000)
    } catch (err) {
      if (err?.response?.status === 409) {
        const detail = err.response.data?.detail
        setConflictData({
          serverContent: detail?.server_content ?? '',
          serverVersion: detail?.server_version ?? version + 1,
        })
        setSaveStatus('conflict')
      } else {
        setSaveStatus('')
      }
    }
  }, [channelId, saveNotes])

  const scheduleSave = useCallback((content, version) => {
    clearTimeout(autosaveTimer.current)
    autosaveTimer.current = setTimeout(() => doSave(content, version), AUTOSAVE_DELAY)
  }, [doSave])

  const handleChange = (value) => {
    setDraft(value)
    setSaveStatus('')
    scheduleSave(value, baseVersion)
  }

  const handleSaveNow = () => {
    clearTimeout(autosaveTimer.current)
    doSave(draft, baseVersion)
  }

  const acceptTheirVersion = () => {
    const serverContent = conflictData?.serverContent ?? ''
    const serverVersion = conflictData?.serverVersion ?? baseVersion
    setDraft(serverContent)
    setBaseVersion(serverVersion)
    setConflictData(null)
    setSaveStatus('')
  }

  const keepMine = () => {
    const serverVersion = conflictData?.serverVersion ?? baseVersion
    setBaseVersion(serverVersion)
    setConflictData(null)
    doSave(draft, serverVersion)
  }

  if (!open) return null

  const content = notes?.content ?? ''
  const hasNotes = Boolean(content.trim())

  return (
    <>
      <div className="channel-notes" data-testid="channel-notes">
        <div className="channel-notes-header">
          <span className="channel-notes-title">📌 Channel Notes</span>
          <div className="channel-notes-actions">
            {notes && (
              <button onClick={() => setShowHistory(true)} title="Revision history">
                History
              </button>
            )}
            <button onClick={() => setEditing((e) => !e)}>
              {editing ? 'Preview' : 'Edit'}
            </button>
            {editing && saveStatus && (
              <span className={`text-[10px] font-mono ml-1 ${saveStatus === 'conflict' ? 'text-[#ff8c42]' : 'text-[var(--text-muted)]'}`}>
                {saveStatus === 'saving' ? 'Saving…' : saveStatus === 'saved' ? 'Saved ✓' : saveStatus === 'conflict' ? '⚠ Conflict' : ''}
              </span>
            )}
          </div>
        </div>

        <div className="channel-notes-body">
          {editing ? (
            <>
              <textarea
                className="notes-textarea"
                value={draft}
                onChange={(e) => handleChange(e.target.value)}
                placeholder="Add notes for this channel… (Markdown supported)"
                spellCheck={false}
              />
              <div className="notes-editor-footer">
                <span className="notes-char-count">{draft.length} chars</span>
                <span className="notes-save-hint">
                  Autosaves ·{' '}
                  <button
                    type="button"
                    onClick={handleSaveNow}
                    className="text-[var(--accent-teal)] underline-offset-2 underline decoration-dotted cursor-pointer bg-transparent border-0 p-0 font-mono text-xs"
                  >
                    Save now
                  </button>
                </span>
              </div>

              {conflictData && (
                <div className="notes-conflict-banner">
                  ⚠ Someone else edited the notes while you were typing.
                  <button onClick={acceptTheirVersion}>Use their version</button>
                  <button onClick={keepMine}>Keep mine (force save)</button>
                </div>
              )}
            </>
          ) : hasNotes ? (
            <MessageContent content={content} />
          ) : (
            <p className="text-xs font-mono text-[var(--text-muted)] py-2">
              No notes yet.{' '}
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="text-[var(--accent-teal)] underline decoration-dotted cursor-pointer bg-transparent border-0 p-0 font-mono text-xs"
              >
                Add some →
              </button>
            </p>
          )}
        </div>
      </div>

      {showHistory && (
        <NotesHistoryModal
          channelId={channelId}
          onClose={() => setShowHistory(false)}
        />
      )}
    </>
  )
}
