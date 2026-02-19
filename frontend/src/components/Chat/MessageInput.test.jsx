import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MessageInput from './MessageInput'
import useChatStore from '../../store/chatStore'

vi.mock('../../store/chatStore', () => ({ default: vi.fn() }))
vi.mock('../../services/uploads', () => ({
  uploadFile: vi.fn(() => Promise.resolve({ id: 99, url: '/uploads/x.png', mime_type: 'image/png', size: 100, original_filename: 'x.png' })),
}))

beforeAll(() => {
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:fake' })
})

afterAll(() => {
  vi.unstubAllGlobals()
})

const mockSendMessage = vi.fn()
const mockFetchMessages = vi.fn()
const mockAddPendingAttachment = vi.fn(() => 'tmp-1')
const mockUpdateAttachmentProgress = vi.fn()
const mockFinalizeAttachment = vi.fn()
const mockSetAttachmentError = vi.fn()
const mockRemovePendingAttachment = vi.fn()
const mockClearPendingAttachments = vi.fn()
const mockClearReplyingTo = vi.fn()

const defaultStore = {
  sendMessage: mockSendMessage,
  activeChannelId: 42,
  fetchMessages: mockFetchMessages,
  pendingAttachments: [],
  addPendingAttachment: mockAddPendingAttachment,
  updateAttachmentProgress: mockUpdateAttachmentProgress,
  finalizeAttachment: mockFinalizeAttachment,
  setAttachmentError: mockSetAttachmentError,
  removePendingAttachment: mockRemovePendingAttachment,
  clearPendingAttachments: mockClearPendingAttachments,
  replyingTo: null,
  clearReplyingTo: mockClearReplyingTo,
}

beforeEach(() => {
  vi.clearAllMocks()
  useChatStore.mockReturnValue(defaultStore)
})

describe('MessageInput', () => {
  it('renders a textarea', () => {
    render(<MessageInput />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('send button is disabled when input is empty and no pending attachments', () => {
    render(<MessageInput />)
    expect(screen.getByTitle(/send/i)).toBeDisabled()
  })

  it('send button becomes enabled when text is entered', async () => {
    render(<MessageInput />)
    await userEvent.type(screen.getByRole('textbox'), 'hello')
    expect(screen.getByTitle(/send/i)).not.toBeDisabled()
  })

  it('calls sendMessage with text and empty ids when Enter is pressed', async () => {
    render(<MessageInput />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'hello world')
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(mockSendMessage).toHaveBeenCalledWith('hello world', [])
  })

  it('does not submit on Shift+Enter', async () => {
    render(<MessageInput />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'hello')
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
    expect(mockSendMessage).not.toHaveBeenCalled()
  })

  it('clears the input after sending', async () => {
    render(<MessageInput />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'hello')
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(textarea.value).toBe('')
  })

  it('calls onTyping callback when typing', async () => {
    const onTyping = vi.fn()
    render(<MessageInput onTyping={onTyping} />)
    await userEvent.type(screen.getByRole('textbox'), 'h')
    expect(onTyping).toHaveBeenCalled()
  })

  it('does not submit when activeChannelId is null', async () => {
    useChatStore.mockReturnValue({ ...defaultStore, activeChannelId: null })
    render(<MessageInput />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'hello')
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(mockSendMessage).not.toHaveBeenCalled()
  })

  it('renders the attach button', () => {
    render(<MessageInput />)
    expect(screen.getByTestId('attach-button')).toBeInTheDocument()
  })

  it('attach button click triggers file input click', async () => {
    render(<MessageInput />)
    const fileInput = screen.getByTestId('file-input')
    const clickSpy = vi.spyOn(fileInput, 'click').mockImplementation(() => {})
    await userEvent.click(screen.getByTestId('attach-button'))
    expect(clickSpy).toHaveBeenCalled()
  })

  it('send button is disabled while an attachment is uploading', () => {
    useChatStore.mockReturnValue({
      ...defaultStore,
      pendingAttachments: [{ tempId: 'tmp-1', file: new File(['x'], 'x.png', { type: 'image/png' }), progress: 50, error: null, id: null }],
    })
    render(<MessageInput />)
    expect(screen.getByTitle(/send/i)).toBeDisabled()
  })

  it('send button is enabled when attachment is done uploading', () => {
    useChatStore.mockReturnValue({
      ...defaultStore,
      pendingAttachments: [{ tempId: 'tmp-1', file: new File(['x'], 'x.png', { type: 'image/png' }), progress: 100, error: null, id: 5 }],
    })
    render(<MessageInput />)
    expect(screen.getByTitle(/send/i)).not.toBeDisabled()
  })

  it('shows reply preview strip when replyingTo is set', () => {
    useChatStore.mockReturnValue({
      ...defaultStore,
      replyingTo: { id: 10, content: 'Original message', user: { username: 'alice' } },
    })
    render(<MessageInput />)
    expect(screen.getByTestId('reply-preview')).toBeInTheDocument()
    expect(screen.getByText('alice')).toBeInTheDocument()
    expect(screen.getByText('Original message')).toBeInTheDocument()
  })

  it('does not show reply preview when replyingTo is null', () => {
    render(<MessageInput />)
    expect(screen.queryByTestId('reply-preview')).toBeNull()
  })

  it('cancel reply button calls clearReplyingTo', async () => {
    useChatStore.mockReturnValue({
      ...defaultStore,
      replyingTo: { id: 10, content: 'Hello', user: { username: 'bob' } },
    })
    render(<MessageInput />)
    await userEvent.click(screen.getByTestId('cancel-reply'))
    expect(mockClearReplyingTo).toHaveBeenCalled()
  })
})
