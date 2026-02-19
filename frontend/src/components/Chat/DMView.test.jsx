import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DMView from './DMView'
import useDMStore from '../../store/dmStore'
import useAuthStore from '../../store/authStore'

vi.mock('../../store/dmStore', () => ({ default: vi.fn() }))
vi.mock('../../store/authStore', () => ({ default: vi.fn() }))
vi.mock('../../hooks/useWebSocketDM', () => ({ useWebSocketDM: vi.fn() }))

// jsdom does not implement scrollIntoView
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

const mockSendDMMessage = vi.fn()

const baseMessages = [
  {
    id: 1,
    user_id: 2,
    user: { username: 'alice' },
    content: 'Hey there',
    created_at: '2024-01-01T10:00:00Z',
    reactions: [],
    edited_at: null,
    attachments: [],
    reply_to: null,
    reply_to_id: null,
    dm_channel_id: 10,
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.mockReturnValue({ user: { id: 1, username: 'bob' }, token: 'tok' })
  useDMStore.mockReturnValue({
    dmMessages: baseMessages,
    loadingDMMessages: false,
    activeDmId: 10,
    dms: [{ id: 10, other_user: { id: 2, username: 'alice' } }],
    sendDMMessage: mockSendDMMessage,
  })
})

// We also need to mock useChatStore since Message uses it
vi.mock('../../store/chatStore', () => ({
  default: vi.fn(() => ({
    editMessage: vi.fn(),
    deleteMessage: vi.fn(),
    addReaction: vi.fn(),
    removeReaction: vi.fn(),
    setReplyingTo: vi.fn(),
  })),
}))

describe('DMView', () => {
  it('renders the other user header', () => {
    render(<DMView />)
    expect(screen.getByRole('heading', { name: 'alice' })).toBeInTheDocument()
  })

  it('renders existing messages', () => {
    render(<DMView />)
    expect(screen.getByText('Hey there')).toBeInTheDocument()
  })

  it('renders loading state', () => {
    useDMStore.mockReturnValue({
      dmMessages: [],
      loadingDMMessages: true,
      activeDmId: 10,
      dms: [{ id: 10, other_user: { id: 2, username: 'alice' } }],
      sendDMMessage: mockSendDMMessage,
    })
    render(<DMView />)
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('renders empty state when no messages', () => {
    useDMStore.mockReturnValue({
      dmMessages: [],
      loadingDMMessages: false,
      activeDmId: 10,
      dms: [{ id: 10, other_user: { id: 2, username: 'alice' } }],
      sendDMMessage: mockSendDMMessage,
    })
    render(<DMView />)
    expect(screen.getByText(/No messages yet/i)).toBeInTheDocument()
  })

  it('send button is disabled when input is empty', () => {
    render(<DMView />)
    expect(screen.getByTestId('dm-send-button')).toBeDisabled()
  })

  it('send button is enabled when text is entered', async () => {
    render(<DMView />)
    await userEvent.type(screen.getByTestId('dm-input'), 'hello')
    expect(screen.getByTestId('dm-send-button')).not.toBeDisabled()
  })

  it('calls sendDMMessage when Enter is pressed with text', async () => {
    render(<DMView />)
    const input = screen.getByTestId('dm-input')
    await userEvent.type(input, 'hello')
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false })
    expect(mockSendDMMessage).toHaveBeenCalledWith('hello')
  })

  it('clears input after sending', async () => {
    render(<DMView />)
    const input = screen.getByTestId('dm-input')
    await userEvent.type(input, 'hello')
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false })
    expect(input.value).toBe('')
  })

  it('does not send on Shift+Enter', async () => {
    render(<DMView />)
    const input = screen.getByTestId('dm-input')
    await userEvent.type(input, 'hello')
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    expect(mockSendDMMessage).not.toHaveBeenCalled()
  })
})
