import { useState, useRef, useEffect } from 'react'

function fmtTime(secs) {
  const t = Math.max(0, Math.round(secs))
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`
}

export default function VoiceMessagePlayer({ url, durationSecs }) {
  const audioRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState(durationSecs ?? 0)

  useEffect(() => {
    const el = audioRef.current
    if (!el) return

    const onTime = () => setCurrent(el.currentTime)
    const onDur = () => setDuration(isFinite(el.duration) ? el.duration : (durationSecs ?? 0))
    const onEnd = () => { setPlaying(false); setCurrent(0) }

    el.addEventListener('timeupdate', onTime)
    el.addEventListener('loadedmetadata', onDur)
    el.addEventListener('ended', onEnd)
    return () => {
      el.removeEventListener('timeupdate', onTime)
      el.removeEventListener('loadedmetadata', onDur)
      el.removeEventListener('ended', onEnd)
    }
  }, [durationSecs])

  const toggle = () => {
    const el = audioRef.current
    if (!el) return
    if (playing) {
      el.pause()
      setPlaying(false)
    } else {
      el.play()
      setPlaying(true)
    }
  }

  const pct = duration > 0 ? Math.min((current / duration) * 100, 100) : 0

  return (
    <div
      className="
        flex items-center gap-2.5 px-3 py-2 rounded border border-[var(--border)]
        bg-black/40 hover:border-[var(--border-glow)] transition-all max-w-xs
      "
      data-testid="voice-player"
    >
      <audio ref={audioRef} src={url} preload="metadata" />

      {/* Play / Pause */}
      <button
        onClick={toggle}
        className="
          w-7 h-7 flex items-center justify-center rounded-full flex-shrink-0
          border border-[var(--border-glow)] text-[var(--accent-teal)] text-xs
          hover:bg-[var(--accent-teal)]/10 transition-all
        "
        title={playing ? 'Pause' : 'Play'}
      >
        {playing ? '⏸' : '▶'}
      </button>

      {/* Progress track */}
      <div className="flex-1 h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
        <div
          className="h-full bg-[var(--accent-teal)] rounded-full transition-all duration-150"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Time */}
      <span className="text-[10px] font-mono text-[var(--text-muted)] flex-shrink-0 tabular-nums">
        {fmtTime(playing ? current : duration)}
      </span>
    </div>
  )
}
