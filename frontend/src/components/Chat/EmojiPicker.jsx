/**
 * EmojiPicker — themed emoji picker popover.
 *
 * Lazy-loads @emoji-mart/react so the heavy emoji data bundle is excluded
 * from the initial JS chunk.  Handles click-outside / Escape dismissal and
 * skin-tone persistence via localStorage.
 *
 * Props:
 *   onSelect(emoji: string) — called with the native emoji character
 *   onClose()               — called when the picker should close
 *   anchorRef               — ref to the button that opened the picker;
 *                             clicking the anchor won't re-trigger onClose
 *   positionClass           — Tailwind absolute-position classes
 *                             (default: 'bottom-full left-0')
 */
import { lazy, Suspense, useEffect, useRef } from 'react'

const SKIN_TONE_KEY = 'chisme_emoji_skin'

export function getSavedSkinTone() {
  const saved = localStorage.getItem(SKIN_TONE_KEY)
  const n = parseInt(saved, 10)
  return n >= 1 && n <= 6 ? n : 1
}

export function saveSkinTone(skin) {
  if (skin >= 1 && skin <= 6) {
    localStorage.setItem(SKIN_TONE_KEY, String(skin))
  }
}

// The heavy chunk — loaded only when the picker is first opened.
const EmojiPickerLazy = lazy(() => import('./EmojiPickerLazy'))

export default function EmojiPicker({
  onSelect,
  onClose,
  anchorRef = null,
  positionClass = 'bottom-full left-0',
}) {
  const containerRef = useRef(null)
  const defaultSkin = getSavedSkinTone()

  // Close when clicking outside both the picker and the anchor button
  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current?.contains(e.target)) return
      if (anchorRef?.current?.contains(e.target)) return
      onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose, anchorRef])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const handleSelect = (emoji) => {
    // Persist non-default skin tones (2-6). Skin=1 is the default yellow; skip it.
    if (emoji.skin > 1) saveSkinTone(emoji.skin)
    onSelect(emoji.native)
    onClose()
  }

  return (
    <div
      ref={containerRef}
      className={`absolute ${positionClass} mb-2 z-30 rounded-lg overflow-hidden
                  w-80 max-w-[calc(100vw-2rem)]
                  border border-[var(--border-glow)]
                  shadow-[0_0_20px_rgba(0,206,209,0.3)]`}
      data-testid="emoji-picker"
    >
      <Suspense
        fallback={
          <div
            className="w-80 h-48 flex items-center justify-center
                       bg-[var(--bg-secondary)] text-[var(--text-muted)] font-mono text-xs"
            data-testid="emoji-picker-loading"
          >
            loading…
          </div>
        }
      >
        <EmojiPickerLazy onEmojiSelect={handleSelect} defaultSkin={defaultSkin} />
      </Suspense>
    </div>
  )
}
