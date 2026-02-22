import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useWebSocket } from './useWebSocket'
import useChatStore from '../store/chatStore'

// The hook calls both useChatStore(selector) and useChatStore.getState() directly,
// so the mock needs to work as a callable selector AND expose getState as a method.
vi.mock('../store/chatStore', () => {
  const mock = vi.fn()
  mock.getState = vi.fn(() => ({ activeChannelId: 1 }))
  return { default: mock }
})

const mockAppendMessageForChannel = vi.fn()
const mockIncrementUnread = vi.fn()
const mockUpdateMessage = vi.fn()
const mockRemoveMessage = vi.fn()
const mockSetTypingUsers = vi.fn()
const mockSetVoiceUser = vi.fn()
const mockRemoveVoiceUser = vi.fn()
const mockPushVoiceSignal = vi.fn()
const mockSetChannelVoiceCount = vi.fn()
const mockAdjustChannelVoiceCount = vi.fn()

beforeEach(() => {
  useChatStore.mockImplementation((sel) =>
    sel({
      appendMessageForChannel: mockAppendMessageForChannel,
      incrementUnread: mockIncrementUnread,
      updateMessage: mockUpdateMessage,
      removeMessage: mockRemoveMessage,
      setTypingUsers: mockSetTypingUsers,
      setVoiceUser: mockSetVoiceUser,
      removeVoiceUser: mockRemoveVoiceUser,
      pushVoiceSignal: mockPushVoiceSignal,
      setChannelVoiceCount: mockSetChannelVoiceCount,
      adjustChannelVoiceCount: mockAdjustChannelVoiceCount,
    })
  )
  // Active channel matches channel_id in test payloads so message.new is appended
  useChatStore.getState.mockReturnValue({ activeChannelId: 1 })
})

function getInstance() {
  return global.WebSocket._instances.at(-1)
}

describe('useWebSocket', () => {
  it('creates a server-level WebSocket on mount', async () => {
    renderHook(() => useWebSocket(1, 'tok123'))
    await waitFor(() => expect(global.WebSocket._instances.length).toBeGreaterThan(0))
    expect(getInstance().url).toMatch(/\/ws\/server\/1/)
  })

  it('sends auth message after connection opens', async () => {
    renderHook(() => useWebSocket(1, 'mytoken'))
    await waitFor(() => getInstance()?.sent.length > 0)
    const msg = JSON.parse(getInstance().sent[0])
    expect(msg).toEqual({ type: 'auth', token: 'mytoken' })
  })

  it('calls appendMessageForChannel on message.new for the active channel', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({
        data: JSON.stringify({
          type: 'message.new',
          channel_id: 1,
          message: { id: 5, content: 'hi' },
        }),
      })
    })
    expect(mockAppendMessageForChannel).toHaveBeenCalledWith(1, { id: 5, content: 'hi' })
  })

  it('calls updateMessage on message.updated event', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({
        data: JSON.stringify({ type: 'message.updated', message: { id: 5, content: 'edited' } }),
      })
    })
    expect(mockUpdateMessage).toHaveBeenCalledWith({ id: 5, content: 'edited' })
  })

  it('calls removeMessage on message.deleted event', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({
        data: JSON.stringify({ type: 'message.deleted', message_id: 5 }),
      })
    })
    expect(mockRemoveMessage).toHaveBeenCalledWith(5)
  })

  it('calls setTypingUsers on user.typing for the active channel', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({
        data: JSON.stringify({ type: 'user.typing', channel_id: 1, username: 'bob' }),
      })
    })
    expect(mockSetTypingUsers).toHaveBeenCalled()
  })

  it('ignores user.typing for a non-active channel', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({
        data: JSON.stringify({ type: 'user.typing', channel_id: 99, username: 'bob' }),
      })
    })
    expect(mockSetTypingUsers).not.toHaveBeenCalled()
  })

  it('increments unread for message.new in a non-active channel', async () => {
    renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => {
      getInstance().onmessage({
        data: JSON.stringify({
          type: 'message.new',
          channel_id: 99,
          message: { id: 6, content: 'other' },
        }),
      })
    })
    expect(mockIncrementUnread).toHaveBeenCalledWith(99)
    expect(mockAppendMessageForChannel).not.toHaveBeenCalled()
  })

  it('closes the WebSocket on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    unmount()
    expect(getInstance().readyState).toBe(WebSocket.CLOSED)
  })

  it('does not create a WebSocket when serverId is null', () => {
    renderHook(() => useWebSocket(null, 'tok'))
    expect(global.WebSocket._instances.length).toBe(0)
  })

  it('does not create a WebSocket when token is null', () => {
    renderHook(() => useWebSocket(1, null))
    expect(global.WebSocket._instances.length).toBe(0)
  })

  it('sendTyping sends the correct payload with channel_id', async () => {
    const { result } = renderHook(() => useWebSocket(1, 'tok'))
    await waitFor(() => getInstance()?.readyState === WebSocket.OPEN)
    act(() => result.current.sendTyping(1))
    const sent = getInstance().sent
    const typingMsg = sent.find((s) => JSON.parse(s).type === 'user.typing')
    expect(typingMsg).toBeDefined()
    expect(JSON.parse(typingMsg)).toMatchObject({ type: 'user.typing', channel_id: 1 })
  })
})
