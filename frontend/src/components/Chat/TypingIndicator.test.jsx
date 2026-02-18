import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import TypingIndicator from './TypingIndicator'
import useChatStore from '../../store/chatStore'
import useAuthStore from '../../store/authStore'

vi.mock('../../store/chatStore', () => ({ default: vi.fn() }))
vi.mock('../../store/authStore', () => ({ default: vi.fn() }))

beforeEach(() => {
  useAuthStore.mockReturnValue({ user: { id: 1, username: 'alice' } })
})

describe('TypingIndicator', () => {
  it('renders nothing when no one is typing', () => {
    useChatStore.mockImplementation((sel) => sel({ typingUsers: [] }))
    const { container } = render(<TypingIndicator />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when only the current user is typing', () => {
    useChatStore.mockImplementation((sel) => sel({ typingUsers: ['alice'] }))
    const { container } = render(<TypingIndicator />)
    expect(container.firstChild).toBeNull()
  })

  it('shows a single user typing', () => {
    useChatStore.mockImplementation((sel) => sel({ typingUsers: ['bob'] }))
    render(<TypingIndicator />)
    expect(screen.getByText(/bob is typing/i)).toBeInTheDocument()
  })

  it('shows two users typing with "and"', () => {
    useChatStore.mockImplementation((sel) => sel({ typingUsers: ['bob', 'carol'] }))
    render(<TypingIndicator />)
    expect(screen.getByText(/bob and carol are typing/i)).toBeInTheDocument()
  })

  it('excludes the current user from the display', () => {
    useChatStore.mockImplementation((sel) => sel({ typingUsers: ['alice', 'bob'] }))
    render(<TypingIndicator />)
    const text = screen.getByText(/typing/)
    expect(text.textContent).not.toMatch(/alice/)
    expect(text.textContent).toMatch(/bob/)
  })

  it('renders three animated dots', () => {
    useChatStore.mockImplementation((sel) => sel({ typingUsers: ['bob'] }))
    const { container } = render(<TypingIndicator />)
    const dots = container.querySelectorAll('span > span')
    expect(dots).toHaveLength(3)
  })
})
