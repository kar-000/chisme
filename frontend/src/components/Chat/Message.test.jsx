import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Message from './Message'
import useAuthStore from '../../store/authStore'
import useChatStore from '../../store/chatStore'

vi.mock('../../store/authStore', () => ({ default: vi.fn() }))
vi.mock('../../store/chatStore', () => ({ default: vi.fn() }))

const mockEditMessage = vi.fn()
const mockDeleteMessage = vi.fn()
const mockAddReaction = vi.fn()
const mockRemoveReaction = vi.fn()

const baseMessage = {
  id: 1,
  user_id: 2,
  user: { username: 'bob' },
  content: 'Hello world',
  created_at: '2024-01-01T10:30:00Z',
  reactions: [],
  edited_at: null,
  attachments: [],
}

beforeEach(() => {
  useAuthStore.mockReturnValue({ user: { id: 1, username: 'alice' } })
  useChatStore.mockReturnValue({
    editMessage: mockEditMessage,
    deleteMessage: mockDeleteMessage,
    addReaction: mockAddReaction,
    removeReaction: mockRemoveReaction,
  })
})

describe('Message', () => {
  it('renders the username', () => {
    render(<Message message={baseMessage} />)
    expect(screen.getByText('bob')).toBeInTheDocument()
  })

  it('renders the message content', () => {
    render(<Message message={baseMessage} />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
  })

  it('renders a formatted timestamp', () => {
    render(<Message message={baseMessage} />)
    // The time is formatted with toLocaleTimeString — just check something time-like exists
    expect(screen.getByText(/\d{1,2}:\d{2}/)).toBeInTheDocument()
  })

  it('shows "(edited)" when edited_at is set', () => {
    render(<Message message={{ ...baseMessage, edited_at: '2024-01-01T11:00:00Z' }} />)
    expect(screen.getByText('(edited)')).toBeInTheDocument()
  })

  it('does not show "(edited)" when edited_at is null', () => {
    render(<Message message={baseMessage} />)
    expect(screen.queryByText('(edited)')).toBeNull()
  })

  it('renders grouped reactions', () => {
    const message = {
      ...baseMessage,
      reactions: [
        { emoji: '👍', user_id: 99 },
        { emoji: '👍', user_id: 88 },
      ],
    }
    render(<Message message={message} />)
    expect(screen.getByText('👍')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('applies own-message styling when message belongs to current user', () => {
    const ownMessage = { ...baseMessage, user_id: 1 }
    const { container } = render(<Message message={ownMessage} />)
    expect(container.firstChild.className).toMatch(/rgba\(255,182,193/)
  })

  it('shows edit and delete buttons on hover for own messages', async () => {
    const ownMessage = { ...baseMessage, user_id: 1 }
    const { container } = render(<Message message={ownMessage} />)
    fireEvent.mouseEnter(container.firstChild)
    expect(screen.getByTitle('Edit')).toBeInTheDocument()
    expect(screen.getByTitle('Delete')).toBeInTheDocument()
  })

  it('does not show edit/delete for other users messages', async () => {
    const { container } = render(<Message message={baseMessage} />)
    fireEvent.mouseEnter(container.firstChild)
    expect(screen.queryByTitle('Edit')).toBeNull()
    expect(screen.queryByTitle('Delete')).toBeNull()
  })

  it('calls deleteMessage when delete is confirmed', async () => {
    vi.stubGlobal('confirm', () => true)
    const ownMessage = { ...baseMessage, user_id: 1 }
    const { container } = render(<Message message={ownMessage} />)
    fireEvent.mouseEnter(container.firstChild)
    await userEvent.click(screen.getByTitle('Delete'))
    expect(mockDeleteMessage).toHaveBeenCalledWith(1)
    vi.unstubAllGlobals()
  })

  it('calls addReaction when a quick-react emoji is clicked', async () => {
    const { container } = render(<Message message={baseMessage} />)
    fireEvent.mouseEnter(container.firstChild)
    await userEvent.click(screen.getByTitle('React 👍'))
    expect(mockAddReaction).toHaveBeenCalledWith(1, '👍')
  })

  it('renders an image attachment as an img tag', () => {
    const message = {
      ...baseMessage,
      attachments: [{ id: 10, mime_type: 'image/png', url: '/uploads/img.png', original_filename: 'img.png', size: 1024 }],
    }
    render(<Message message={message} />)
    expect(screen.getByTestId('attachment-image')).toBeInTheDocument()
    expect(screen.getByTestId('attachment-image').src).toContain('/uploads/img.png')
  })

  it('opens lightbox when image is clicked', async () => {
    const message = {
      ...baseMessage,
      attachments: [{ id: 10, mime_type: 'image/png', url: '/uploads/img.png', original_filename: 'img.png', size: 1024 }],
    }
    render(<Message message={message} />)
    await userEvent.click(screen.getByTestId('attachment-image'))
    expect(screen.getByTestId('lightbox')).toBeInTheDocument()
  })

  it('closes lightbox when backdrop is clicked', async () => {
    const message = {
      ...baseMessage,
      attachments: [{ id: 10, mime_type: 'image/png', url: '/uploads/img.png', original_filename: 'img.png', size: 1024 }],
    }
    render(<Message message={message} />)
    await userEvent.click(screen.getByTestId('attachment-image'))
    await userEvent.click(screen.getByTestId('lightbox'))
    expect(screen.queryByTestId('lightbox')).toBeNull()
  })

  it('renders a file download card for non-image attachments', () => {
    const message = {
      ...baseMessage,
      attachments: [{ id: 11, mime_type: 'application/pdf', url: '/uploads/doc.pdf', original_filename: 'doc.pdf', size: 2048 }],
    }
    render(<Message message={message} />)
    const card = screen.getByTestId('attachment-file')
    expect(card).toBeInTheDocument()
    expect(card.href).toContain('/uploads/doc.pdf')
    expect(screen.getByText('doc.pdf')).toBeInTheDocument()
  })

  it('renders a video element for video attachments', () => {
    const message = {
      ...baseMessage,
      attachments: [{ id: 12, mime_type: 'video/mp4', url: '/uploads/clip.mp4', original_filename: 'clip.mp4', size: 1048576 }],
    }
    render(<Message message={message} />)
    expect(screen.getByTestId('attachment-video')).toBeInTheDocument()
  })
})
