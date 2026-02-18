import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MessageInput from './MessageInput'
import useChatStore from '../../store/chatStore'

vi.mock('../../store/chatStore', () => ({ default: vi.fn() }))

const mockSendMessage = vi.fn()
const mockFetchMessages = vi.fn()

beforeEach(() => {
  useChatStore.mockReturnValue({
    sendMessage: mockSendMessage,
    activeChannelId: 42,
    fetchMessages: mockFetchMessages,
  })
})

describe('MessageInput', () => {
  it('renders a textarea', () => {
    render(<MessageInput />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('send button is disabled when input is empty', () => {
    render(<MessageInput />)
    expect(screen.getByTitle(/send/i)).toBeDisabled()
  })

  it('send button becomes enabled when text is entered', async () => {
    render(<MessageInput />)
    await userEvent.type(screen.getByRole('textbox'), 'hello')
    expect(screen.getByTitle(/send/i)).not.toBeDisabled()
  })

  it('calls sendMessage when Enter is pressed', async () => {
    render(<MessageInput />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'hello world')
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(mockSendMessage).toHaveBeenCalledWith('hello world')
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
    useChatStore.mockReturnValue({
      sendMessage: mockSendMessage,
      activeChannelId: null,
      fetchMessages: mockFetchMessages,
    })
    render(<MessageInput />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'hello')
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(mockSendMessage).not.toHaveBeenCalled()
  })
})
