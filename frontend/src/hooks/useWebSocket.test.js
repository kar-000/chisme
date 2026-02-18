import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useWebSocket } from './useWebSocket'
import useChatStore from '../store/chatStore'

vi.mock('../store/chatStore', () => ({ default: vi.fn() }))

const mockAppendMessage = vi.fn()
const mockUpdateMessage = vi.fn()
const mockRemoveMessage = vi.fn()
const mockSetTypingUsers = vi.fn()

beforeEach(() => {
  useChatStore.mockImplementation((sel) =>
    sel({
      appendMessage: mockAppendMessage,
      updateMessage: mockUpdateMessage,
      removeMessage: mockRemoveMessage,
      setTypingUsers: mockSetTypingUsers,
    })
  )
})

function getInstance() {
  return global.WebSocket._instances.at(-1)
}

describe('useWebSocket', () => {
  it('creates a WebSocket for the correct channel on mount', async () => {
    renderHook(() => useWebSocket(1, 'tok123'))
    await waitFor(() => expect(global.WebSocket._instances.length).toBeGreaterThan(0))
    expect(getInstance().url).toMatch(/\/ws\/channels\/1/)
  })

  it('sends auth message after connection opens', async () => {
    renderHook(() => useWebSocket(1, 'mytoken'))
    await waitFor(() => getInstance()?.sent.length > 0)
    const msg = JSON.parse(getInstance().sent[0])
    expect(msg).toEqual({ type: 'auth', token: 'mytoken' })
  })

  it('calls appendMessage on message.new event', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({ data: JSON.stringify({ type: 'message.new', message: { id: 5, content: 'hi' } }) })
    })
    expect(mockAppendMessage).toHaveBeenCalledWith({ id: 5, content: 'hi' })
  })

  it('calls updateMessage on message.updated event', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({ data: JSON.stringify({ type: 'message.updated', message: { id: 5, content: 'edited' } }) })
    })
    expect(mockUpdateMessage).toHaveBeenCalledWith({ id: 5, content: 'edited' })
  })

  it('calls removeMessage on message.deleted event', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({ data: JSON.stringify({ type: 'message.deleted', message_id: 5 }) })
    })
    expect(mockRemoveMessage).toHaveBeenCalledWith(5)
  })

  it('calls setTypingUsers on user.typing event', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({ data: JSON.stringify({ type: 'user.typing', username: 'bob' }) })
    })
    expect(mockSetTypingUsers).toHaveBeenCalled()
  })

  it('closes the WebSocket on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    unmount()
    expect(getInstance().readyState).toBe(WebSocket.CLOSED)
  })

  it('does not create a WebSocket when channelId is null', () => {
    renderHook(() => useWebSocket(null, 'tok'))
    expect(global.WebSocket._instances.length).toBe(0)
  })

  it('does not create a WebSocket when token is null', () => {
    renderHook(() => useWebSocket(1, null))
    expect(global.WebSocket._instances.length).toBe(0)
  })

  it('sendTyping sends the correct payload when WS is open', async () => {
    const { result } = renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => result.current.sendTyping())
    const sent = getInstance().sent
    const typingMsg = sent.find((s) => JSON.parse(s).type === 'user.typing')
    expect(typingMsg).toBeDefined()
  })
})
