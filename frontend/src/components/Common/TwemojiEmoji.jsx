/**
 * TwemojiEmoji — renders a single emoji as a Twemoji SVG image.
 *
 * Replaces the OS-native glyph with a consistent Twemoji image so
 * reactions look identical across Windows, macOS, and Linux.
 *
 * NOT used inside the raw textarea (performance) or inside the
 * emoji-mart picker (it handles its own rendering).
 */
import twemoji from '@twemoji/api'

// jsDelivr-hosted SVGs from the jdecked/twemoji fork (maintained successor to twitter/twemoji)
const TWEMOJI_SVG_BASE = 'https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg/'

export default function TwemojiEmoji({ emoji, size = '1.2em', className = '' }) {
  const codepoint = twemoji.convert.toCodePoint(emoji)
  const src = `${TWEMOJI_SVG_BASE}${codepoint}.svg`

  return (
    <img
      src={src}
      alt={emoji}
      className={className}
      style={{
        width: size,
        height: size,
        display: 'inline-block',
        verticalAlign: '-0.15em',
      }}
      draggable={false}
    />
  )
}
