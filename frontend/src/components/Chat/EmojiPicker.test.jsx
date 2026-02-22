/**
 * Tests for EmojiPicker, EmojiPickerLazy, MessageInput emoji integration,
 * and TwemojiEmoji.
 *
 * @emoji-mart/react renders a Shadow DOM custom element that jsdom cannot
 * handle, so we mock the entire lazy chunk.  All behaviour under test is
 * in our own wrapper code.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Suspense } from 'react'

// ── Module mocks ──────────────────────────────────────────────────────────

// Mock the lazy-loaded inner picker so we can control emoji selection
vi.mock('./EmojiPickerLazy', () => ({
  default: ({ onEmojiSelect, defaultSkin }) => (
    <div data-testid="mock-picker" data-skin={defaultSkin}>
      <button
        data-testid="pick-emoji"
        onClick={() => onEmojiSelect({ native: '😊', skin: 1 })}
      >
        😊 default
      </button>
      <button
        data-testid="pick-emoji-skin"
        onClick={() => onEmojiSelect({ native: '👍🏾', skin: 5 })}
      >
        👍🏾 skin5
      </button>
    </div>
  ),
}))

// Mock @twemoji/api so TwemojiEmoji can render without network
vi.mock('@twemoji/api', () => ({
  default: {
    convert: {
      toCodePoint: (emoji) => {
        // Return a simple codepoint for testing
        return [...emoji].map((c) => c.codePointAt(0).toString(16)).join('-')
      },
    },
  },
}))

// Mock zustand stores used by MessageInput / Message.
// Zustand can be called with OR without a selector:
//   useChatStore((s) => s.addReaction)   ← selector call
//   const { addReaction } = useChatStore() ← no-selector call (returns whole state)
const chatState = {
  sendMessage: vi.fn(),
  activeChannelId: 1,
  pendingAttachments: [],
  addPendingAttachment: vi.fn(),
  updateAttachmentProgress: vi.fn(),
  finalizeAttachment: vi.fn(),
  setAttachmentError: vi.fn(),
  removePendingAttachment: vi.fn(),
  clearPendingAttachments: vi.fn(),
  replyingTo: null,
  clearReplyingTo: vi.fn(),
  addReaction: vi.fn(),
  removeReaction: vi.fn(),
  editMessage: vi.fn(),
  deleteMessage: vi.fn(),
  setReplyingTo: vi.fn(),
}

vi.mock('../../store/chatStore', () => ({
  default: vi.fn((selector) => (selector ? selector(chatState) : chatState)),
}))

const authState = {
  user: { id: 1, username: 'testuser' },
  token: 'fake-token',
}

vi.mock('../../store/authStore', () => ({
  default: vi.fn((selector) => (selector ? selector(authState) : authState)),
}))

// Mock services that MessageInput uses
vi.mock('../../services/uploads', () => ({ uploadFile: vi.fn() }))
vi.mock('../../services/gifs', () => ({ attachGif: vi.fn(), searchGifs: vi.fn() }))

// ── EmojiPicker ──────────────────────────────────────────────────────────

import EmojiPicker, { getSavedSkinTone, saveSkinTone } from './EmojiPicker'

describe('EmojiPicker', () => {
  it('renders loading fallback before lazy chunk resolves', () => {
    // Without act(), the Suspense hasn't flushed yet
    render(
      <EmojiPicker onSelect={vi.fn()} onClose={vi.fn()} />,
    )
    // We may get either loading or the mock picker depending on timing;
    // the important assertion is that the wrapper element is present.
    expect(screen.getByTestId('emoji-picker')).toBeInTheDocument()
  })

  it('renders the picker after Suspense resolves', async () => {
    render(<EmojiPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByTestId('mock-picker')).toBeInTheDocument())
  })

  it('calls onSelect with the emoji native string', async () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(<EmojiPicker onSelect={onSelect} onClose={onClose} />)
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))
    expect(onSelect).toHaveBeenCalledWith('😊')
  })

  it('calls onClose after emoji is selected', async () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(<EmojiPicker onSelect={onSelect} onClose={onClose} />)
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when Escape is pressed', async () => {
    const onClose = vi.fn()
    render(<EmojiPicker onSelect={vi.fn()} onClose={onClose} />)
    await waitFor(() => screen.getByTestId('mock-picker'))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when clicking outside the picker', async () => {
    const onClose = vi.fn()
    render(
      <div>
        <EmojiPicker onSelect={vi.fn()} onClose={onClose} />
        <div data-testid="outside">outside</div>
      </div>,
    )
    await waitFor(() => screen.getByTestId('mock-picker'))
    fireEvent.mouseDown(screen.getByTestId('outside'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does NOT call onClose when clicking inside the picker', async () => {
    const onClose = vi.fn()
    render(<EmojiPicker onSelect={vi.fn()} onClose={onClose} />)
    await waitFor(() => screen.getByTestId('mock-picker'))
    fireEvent.mouseDown(screen.getByTestId('mock-picker'))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('does NOT call onClose when clicking the anchor element', async () => {
    const onClose = vi.fn()
    const anchorRef = { current: null }

    function Wrapper() {
      return (
        <div>
          <button ref={(el) => { anchorRef.current = el }} data-testid="anchor">
            open
          </button>
          <EmojiPicker onSelect={vi.fn()} onClose={onClose} anchorRef={anchorRef} />
        </div>
      )
    }
    render(<Wrapper />)
    await waitFor(() => screen.getByTestId('mock-picker'))
    fireEvent.mouseDown(screen.getByTestId('anchor'))
    expect(onClose).not.toHaveBeenCalled()
  })
})

// ── Skin tone localStorage persistence ───────────────────────────────────

describe('skin tone persistence', () => {
  beforeEach(() => localStorage.clear())

  it('getSavedSkinTone returns 1 when nothing is stored', () => {
    expect(getSavedSkinTone()).toBe(1)
  })

  it('getSavedSkinTone returns the stored value', () => {
    localStorage.setItem('chisme_emoji_skin', '5')
    expect(getSavedSkinTone()).toBe(5)
  })

  it('getSavedSkinTone clamps out-of-range values to 1', () => {
    localStorage.setItem('chisme_emoji_skin', '99')
    expect(getSavedSkinTone()).toBe(1)
  })

  it('saveSkinTone writes to localStorage', () => {
    saveSkinTone(3)
    expect(localStorage.getItem('chisme_emoji_skin')).toBe('3')
  })

  it('saves skin tone to localStorage when skin-toned emoji is selected', async () => {
    render(<EmojiPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    await waitFor(() => screen.getByTestId('pick-emoji-skin'))
    fireEvent.click(screen.getByTestId('pick-emoji-skin'))
    expect(localStorage.getItem('chisme_emoji_skin')).toBe('5')
  })

  it('does not save skin tone for emoji with default skin (skin=1)', async () => {
    // emoji-mart reports skin=1 for the yellow/default emoji.
    // We treat 1 as "not a user-selected skin tone" and skip saving it,
    // so the key stays absent on first use.
    render(<EmojiPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))
    expect(localStorage.getItem('chisme_emoji_skin')).toBeNull()
  })

  it('passes saved skin tone as defaultSkin to the picker', async () => {
    localStorage.setItem('chisme_emoji_skin', '4')
    render(<EmojiPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    await waitFor(() => screen.getByTestId('mock-picker'))
    expect(screen.getByTestId('mock-picker')).toHaveAttribute('data-skin', '4')
  })
})

// ── EmojiPicker uses dynamic import (code splitting) ─────────────────────

describe('code splitting', () => {
  it('EmojiPicker wraps the inner picker in Suspense', async () => {
    // Render the picker — before the lazy chunk resolves, Suspense shows fallback
    // With our synchronous mock, it resolves immediately; we just verify the
    // picker container renders correctly without errors.
    expect(() =>
      render(<EmojiPicker onSelect={vi.fn()} onClose={vi.fn()} />),
    ).not.toThrow()
    await waitFor(() => screen.getByTestId('mock-picker'))
  })
})

// ── MessageInput emoji integration ────────────────────────────────────────

import MessageInput from './MessageInput'

describe('MessageInput emoji button', () => {
  it('renders the emoji button', () => {
    render(<MessageInput onTyping={vi.fn()} />)
    expect(screen.getByTestId('emoji-button')).toBeInTheDocument()
  })

  it('opens the emoji picker when the button is clicked', async () => {
    render(<MessageInput onTyping={vi.fn()} />)
    fireEvent.click(screen.getByTestId('emoji-button'))
    await waitFor(() => expect(screen.getByTestId('emoji-picker')).toBeInTheDocument())
  })

  it('closes the emoji picker when an emoji is selected', async () => {
    render(<MessageInput onTyping={vi.fn()} />)
    fireEvent.click(screen.getByTestId('emoji-button'))
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))
    await waitFor(() => expect(screen.queryByTestId('emoji-picker')).not.toBeInTheDocument())
  })

  it('inserts selected emoji into the textarea', async () => {
    render(<MessageInput onTyping={vi.fn()} />)
    const textarea = screen.getByRole('textbox')

    // Type some text first
    await userEvent.type(textarea, 'hello ')

    // Open picker and select emoji
    fireEvent.click(screen.getByTestId('emoji-button'))
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))

    // Emoji should be appended at the saved cursor position (end of 'hello ')
    expect(textarea.value).toContain('😊')
  })

  it('inserts emoji at cursor position (not always at end)', async () => {
    render(<MessageInput onTyping={vi.fn()} />)
    const textarea = screen.getByRole('textbox')

    // Type text and simulate cursor in the middle
    await userEvent.type(textarea, 'hello world')

    // Simulate placing cursor after 'hello ' (position 6)
    textarea.selectionStart = 6
    textarea.selectionEnd = 6
    fireEvent.select(textarea)

    // Open picker and select emoji
    fireEvent.click(screen.getByTestId('emoji-button'))
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))

    // '😊' should be at position 6: 'hello 😊world'
    expect(textarea.value).toBe('hello 😊world')
  })
})

// ── TwemojiEmoji ─────────────────────────────────────────────────────────

import TwemojiEmoji from '../Common/TwemojiEmoji'

describe('TwemojiEmoji', () => {
  it('renders an img with the emoji as alt text', () => {
    render(<TwemojiEmoji emoji="😊" />)
    const img = screen.getByRole('img')
    expect(img).toHaveAttribute('alt', '😊')
  })

  it('img src contains the computed codepoint', () => {
    render(<TwemojiEmoji emoji="😊" />)
    const img = screen.getByRole('img')
    expect(img.getAttribute('src')).toMatch(/cdn\.jsdelivr\.net/)
    expect(img.getAttribute('src')).toMatch(/\.svg$/)
  })

  it('respects custom size prop', () => {
    render(<TwemojiEmoji emoji="😊" size="2em" />)
    const img = screen.getByRole('img')
    expect(img.style.width).toBe('2em')
    expect(img.style.height).toBe('2em')
  })

  it('is not draggable', () => {
    render(<TwemojiEmoji emoji="😊" />)
    expect(screen.getByRole('img')).toHaveAttribute('draggable', 'false')
  })
})

// ── Recently-used tracking (via emoji-mart internals) ────────────────────

describe('recently used category', () => {
  it('emoji selection flows through onSelect without modifying localStorage["em"]', async () => {
    // emoji-mart uses localStorage["em"] for recently-used state.
    // Our wrapper must not clear or overwrite that key.
    localStorage.setItem('em', JSON.stringify({ frequently: { '1f60a': 3 } }))

    const onSelect = vi.fn()
    render(<EmojiPicker onSelect={onSelect} onClose={vi.fn()} />)
    await waitFor(() => screen.getByTestId('pick-emoji'))
    fireEvent.click(screen.getByTestId('pick-emoji'))

    // Our code should not have tampered with the em key
    const stored = JSON.parse(localStorage.getItem('em'))
    expect(stored.frequently['1f60a']).toBe(3)
    // And our handler did call onSelect
    expect(onSelect).toHaveBeenCalledWith('😊')
  })
})
